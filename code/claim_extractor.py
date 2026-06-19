"""Deterministic multilingual extraction of the actual damage claim."""

from __future__ import annotations

import re

from config import OBJECT_PARTS
from utils import ClaimIntent, customer_utterances, normalize_text

PART_PATTERNS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "car": [
        ("rear_bumper", ("rear bumper", "back bumper", "bumper trasero", "parachoques trasero",
                         "parachoques de atras", "piche ka bumper", "back ka bumper")),
        ("front_bumper", ("front bumper", "bumper delantero", "parachoques delantero",
                          "aage ka bumper", "front side bumper")),
        ("side_mirror", ("side mirror", "wing mirror", "door mirror", "espejo lateral",
                         "left mirror", "right mirror")),
        ("windshield", ("windshield", "windscreen", "front glass", "parabrisas", "sheesha")),
        ("taillight", ("taillight", "tail light", "back light", "rear light", "luz trasera")),
        ("headlight", ("headlight", "head light", "front light", "faro")),
        ("quarter_panel", ("quarter panel",)),
        ("fender", ("fender", "mudguard")),
        ("hood", ("hood", "bonnet", "cofre", "tapa del motor")),
        ("door", ("door panel", "car door", "left side door", "right side door", "puerta", "door")),
        ("body", ("body panel", "car body", "vehicle body", "carroceria", "body")),
    ],
    "laptop": [
        ("trackpad", ("trackpad", "touchpad", "mouse pad", "panel tactil")),
        ("keyboard", ("keyboard", "keycap", "keys", "teclas", "teclado", "kunji")),
        ("hinge", ("hinge", "bisagra")),
        ("screen", ("screen", "display", "pantalla", "monitor", "laptop glass")),
        ("lid", ("outer lid", "laptop lid", "top cover", "tapa")),
        ("corner", ("laptop corner", "outer corner", "corner", "esquina")),
        ("port", ("charging port", "usb port", "port", "puerto")),
        ("base", ("laptop base", "bottom case", "base")),
        ("body", ("laptop body", "outer body", "side edge", "palm rest", "chassis", "body")),
    ],
    "package": [
        ("package_corner", ("package corner", "box corner", "cardboard box corner",
                            "parcel corner", "esquina", "corner dab")),
        ("package_side", ("package side", "box side", "package surface", "outside", "surface")),
        ("seal", ("seal", "tape", "flap", "sealed side", "seal wali side")),
        ("label", ("shipping label", "package label", "etiqueta", "label")),
        ("contents", ("contents", "content", "product inside", "missing product",
                      "item missing", "andar ka item", "inside the package")),
        ("item", ("inside item", "item inside", "product", "inner item")),
        ("box", ("shipping box", "delivery box", "cardboard box", "package", "parcel", "box")),
    ],
}

ISSUE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("glass_shatter", ("shattered", "shatter", "smashed glass", "screen shattered",
                       "windshield shatter")),
    ("torn_packaging", ("torn open", "torn-open", "torn packaging", "seal is torn",
                        "seal torn", "phati", "fata", "opened jaisa", "open jaisa")),
    ("crushed_packaging", ("crushed", "crush", "dab gaya", "daba hua", "aplastad")),
    ("water_damage", ("water damage", "liquid damage", "wet box", "got wet",
                      "coffee", "water damaged", "mojado", "agua")),
    ("missing_part", ("missing keys", "key is missing", "keys missing", "missing part",
                      "missing or broken", "faltan", "missing")),
    ("broken_part", ("broken", "broke", "breakage", "toot gaya", "toota", "roto")),
    ("dent", ("hail dents", "dented", "dent", "dab gaya", "abollad", "hundido")),
    ("scratch", ("scratched", "scratch", "scrape", "scuff", "rayon")),
    ("crack", ("cracked", "crack", "fracture", "fisura", "rajadura")),
    ("stain", ("oil stain", "stained", "stain", "oily mark", "wet-looking stain",
               "mancha", "daag")),
]


def _find_all(text: str, patterns: list[tuple[str, tuple[str, ...]]]) -> list[str]:
    matches: list[tuple[int, str]] = []
    for label, phrases in patterns:
        positions = [text.find(normalize_text(p)) for p in phrases]
        positions = [p for p in positions if p >= 0]
        if positions:
            matches.append((min(positions), label))
    return [label for _, label in sorted(matches)]


def extract_claim(user_claim: str, claim_object: str) -> ClaimIntent:
    if claim_object not in OBJECT_PARTS:
        raise ValueError(f"Unsupported claim_object: {claim_object}")
    text = normalize_text(customer_utterances(user_claim))
    claimant_segments = []
    for segment in (user_claim or "").split("|"):
        label, sep, content = segment.partition(":")
        if sep and normalize_text(label) in {"customer", "cliente", "user", "claimant"}:
            claimant_segments.append(normalize_text(content))
    final_text = claimant_segments[-1] if claimant_segments else text

    # The final claimant turn commonly narrows or corrects earlier conversational
    # possibilities. Use it first, then fall back to the whole claimant transcript.
    parts = list(dict.fromkeys(_find_all(final_text, PART_PATTERNS[claim_object])))
    negation_prefixes = ("not ", "not the ", "no ", "nahi ", "nahi, ")
    for part, phrases in PART_PATTERNS[claim_object]:
        if any(f"{prefix}{normalize_text(phrase)}" in final_text
               for prefix in negation_prefixes for phrase in phrases):
            parts = [candidate for candidate in parts if candidate != part]
    if "item missing claim nahi" in final_text or "not claiming missing" in final_text:
        parts = [candidate for candidate in parts if candidate not in {"contents", "item"}]
    if not parts:
        parts = list(dict.fromkeys(_find_all(text, PART_PATTERNS[claim_object])))
    if len(parts) > 1:
        parts = [p for p in parts if p not in {"body", "box", "item"}] or parts
    issues = list(dict.fromkeys(
        _find_all(final_text, ISSUE_PATTERNS) + _find_all(text, ISSUE_PATTERNS)
    ))
    if claim_object == "package" and issues and issues[0] == "torn_packaging":
        all_parts = _find_all(text, PART_PATTERNS[claim_object])
        if "seal" in all_parts and parts == ["box"]:
            parts = ["seal"]
    qualifiers = []
    for qualifier, pattern in {
        "severe": r"\b(deep|severe|badly|pretty bad|major)\b",
        "minor": r"\b(small|minor|light|slight|pequeno)\b",
        "left": r"\b(left|izquierd[oa])\b",
        "right": r"\b(right|derech[oa])\b",
        "unreadable": r"\b(unreadable|illegible)\b",
        "instruction_attack": r"\b(ignore .*instructions|approve .*immediately|mark .*supported)\b",
    }.items():
        if re.search(pattern, text):
            qualifiers.append(qualifier)
    return ClaimIntent(
        claim_object=claim_object,
        claimed_parts=parts or ["unknown"],
        claimed_issues=issues or ["unknown"],
        qualifiers=qualifiers,
        source_text=text,
    )
