"""Shared data models, path handling, image utilities, and validation."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageFilter, ImageOps, ImageStat

from config import (
    CLAIM_STATUSES, ISSUE_TYPES, MAX_IMAGE_SIDE, OBJECT_PARTS, OUTPUT_COLUMNS,
    RISK_FLAGS, SEVERITIES,
)


@dataclass
class ClaimIntent:
    claim_object: str
    claimed_parts: list[str]
    claimed_issues: list[str]
    qualifiers: list[str] = field(default_factory=list)
    source_text: str = ""

    @property
    def primary_part(self) -> str:
        return self.claimed_parts[0] if self.claimed_parts else "unknown"

    @property
    def primary_issue(self) -> str:
        return self.claimed_issues[0] if self.claimed_issues else "unknown"


@dataclass
class ImageObservation:
    image_id: str
    visible_object: str = "unknown"
    visible_part: str = "unknown"
    visible_damage: str = "unknown"
    damage_present: bool | None = None
    claimed_part_visible: bool = False
    claimed_condition_visible: bool = False
    severity: str = "unknown"
    quality_issues: list[str] = field(default_factory=list)
    confidence: float = 0.0
    description: str = ""
    original_photo_likely: bool = True
    text_instruction_present: bool = False
    technical_valid: bool = True
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_seconds: float = 0.0
    cache_hit: bool = False


@dataclass
class EvidenceResult:
    evidence_standard_met: bool
    valid_image: bool
    reason: str
    relevant_image_ids: list[str]
    requirement_ids: list[str] = field(default_factory=list)


@dataclass
class DecisionResult:
    issue_type: str
    object_part: str
    claim_status: str
    severity: str
    supporting_image_ids: list[str]
    justification: str


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = normalized.lower().replace("_", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def customer_utterances(transcript: str) -> str:
    pieces = [p.strip() for p in (transcript or "").split("|")]
    claimant = []
    for piece in pieces:
        label, sep, content = piece.partition(":")
        if sep and normalize_text(label) in {"customer", "cliente", "user", "claimant"}:
            claimant.append(content.strip())
    return " ".join(claimant) if claimant else transcript


def split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def image_id(path: str | Path) -> str:
    return Path(path).stem


def resolve_image_path(dataset_dir: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return candidate.resolve()
    from_dataset = (dataset_dir / candidate).resolve()
    if from_dataset.exists():
        return from_dataset
    return (dataset_dir.parent / candidate).resolve()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def encode_image(path: Path, max_side: int = MAX_IMAGE_SIDE) -> tuple[str, dict[str, Any]]:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        original_size = image.size
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        gray = image.convert("L")
        brightness = float(ImageStat.Stat(gray).mean[0])
        edge_variance = float(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).var[0])
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=88, optimize=True)
        data = base64.b64encode(buffer.getvalue()).decode("ascii")
        metadata = {
            "original_width": original_size[0], "original_height": original_size[1],
            "width": image.width, "height": image.height, "brightness": brightness,
            "edge_variance": edge_variance, "low_light": brightness < 35,
            "likely_blurry": edge_variance < 45,
        }
        return f"data:image/jpeg;base64,{data}", metadata


def canonical_flags(flags: Iterable[str]) -> list[str]:
    selected = set(flags)
    return [flag for flag in RISK_FLAGS if flag in selected]


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def validate_output(row: dict[str, Any]) -> dict[str, str]:
    result = {column: str(row.get(column, "")) for column in OUTPUT_COLUMNS}
    if result["evidence_standard_met"] not in {"true", "false"}:
        raise ValueError("evidence_standard_met must be true or false")
    if result["valid_image"] not in {"true", "false"}:
        raise ValueError("valid_image must be true or false")
    if result["issue_type"] not in ISSUE_TYPES:
        raise ValueError(f"Invalid issue_type: {result['issue_type']}")
    obj = result["claim_object"]
    if obj not in OBJECT_PARTS or result["object_part"] not in OBJECT_PARTS[obj]:
        raise ValueError(f"Invalid object_part {result['object_part']} for {obj}")
    if result["claim_status"] not in CLAIM_STATUSES:
        raise ValueError(f"Invalid claim_status: {result['claim_status']}")
    if result["severity"] not in SEVERITIES:
        raise ValueError(f"Invalid severity: {result['severity']}")
    flags = split_semicolon(result["risk_flags"])
    if flags != ["none"] and any(flag not in RISK_FLAGS for flag in flags):
        raise ValueError(f"Invalid risk_flags: {flags}")
    return result


def json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(data) if hasattr(data, "__dataclass_fields__") else data
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
