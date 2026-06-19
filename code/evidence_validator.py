"""Deterministic application of evidence_requirements.csv."""

from __future__ import annotations

from utils import ClaimIntent, EvidenceResult, ImageObservation, normalize_text


def _applicable(issue: str, part: str, text: str) -> bool:
    text = normalize_text(text)
    if "general" in text or "reviewability" in text or "multi-image" in text:
        return True
    issue_terms = {
        "dent": ("dent", "scratch"), "scratch": ("dent", "scratch"),
        "crack": ("crack", "broken", "missing"),
        "glass_shatter": ("crack", "broken", "missing"),
        "broken_part": ("crack", "broken", "missing"),
        "missing_part": ("crack", "broken", "missing", "contents", "inner item"),
        "torn_packaging": ("crushed", "torn", "seal"),
        "crushed_packaging": ("crushed", "torn", "seal"),
        "water_damage": ("water", "stain", "label"),
        "stain": ("water", "stain", "label"),
    }
    return any(term in text for term in issue_terms.get(issue, ())) or part.replace("_", " ") in text


def validate_evidence(
    intent: ClaimIntent,
    observations: list[ImageObservation],
    requirements: list[dict[str, str]],
) -> EvidenceResult:
    matching = [
        row for row in requirements
        if row.get("claim_object") in {"all", intent.claim_object}
        and _applicable(intent.primary_issue, intent.primary_part, row.get("applies_to", ""))
    ]
    requirement_ids = [row["requirement_id"] for row in matching]
    technically_valid = [o for o in observations if o.technical_valid]
    relevant = [
        o for o in technically_valid
        if o.claimed_part_visible and o.claimed_condition_visible and o.confidence >= 0.45
    ]
    if not technically_valid:
        return EvidenceResult(False, False, "No submitted image could be opened for automated review.",
                              [], requirement_ids)
    if not any(not o.error for o in technically_valid):
        return EvidenceResult(False, False, "The submitted images could not be analyzed by the vision model.",
                              [], requirement_ids)
    if not relevant:
        part = intent.primary_part.replace("_", " ")
        return EvidenceResult(
            False, True,
            f"The submitted images do not show the claimed {part} clearly enough to verify the condition.",
            [], requirement_ids,
        )
    ids = [o.image_id for o in relevant]
    part = intent.primary_part.replace("_", " ")
    if len(ids) == 1:
        reason = f"Image {ids[0]} shows the claimed {part} clearly enough to evaluate the reported condition."
    else:
        reason = (f"Images {';'.join(ids)} collectively show the claimed {part} clearly enough "
                  "to evaluate the reported condition.")
    return EvidenceResult(True, True, reason, ids, requirement_ids)
