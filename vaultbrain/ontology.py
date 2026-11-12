"""Strict ontology definitions and triple validation for Vault Brain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set, Tuple

ENTITY_TYPES: Set[str] = {
    "NOTE",
    "CONCEPT",
    "PROJECT",
    "TOOL",
    "PERSON",
}

RELATION_TYPES: Set[str] = {
    "RELATES_TO",
    "DEPENDS_ON",
    "IMPLEMENTS",
    "PART_OF",
    "OWNS",
    "MENTIONED_IN",
}

# Permitted edge signatures: (src_type, relation, dst_type)
ALLOWED_SIGNATURES: Set[Tuple[str, str, str]] = {
    ("PROJECT", "DEPENDS_ON", "TOOL"),
    ("PROJECT", "IMPLEMENTS", "CONCEPT"),
    ("PROJECT", "PART_OF", "PROJECT"),
    ("PROJECT", "RELATES_TO", "PROJECT"),
    ("NOTE", "RELATES_TO", "CONCEPT"),
    ("NOTE", "RELATES_TO", "NOTE"),
    ("NOTE", "PART_OF", "PROJECT"),
    ("PERSON", "OWNS", "PROJECT"),
    ("CONCEPT", "MENTIONED_IN", "NOTE"),
    ("TOOL", "MENTIONED_IN", "NOTE"),
    ("CONCEPT", "RELATES_TO", "CONCEPT"),
}


class ValidationError(ValueError):
    """Raised when an extracted entity or relation violates the strict ontology."""
    pass


@dataclass
class Triple:
    src: str
    src_type: str
    rel: str
    dst: str
    dst_type: str
    confidence: float = 1.0
    evidence: str = ""

    def to_dict(self):
        return {
            "src": self.src,
            "src_type": self.src_type,
            "rel": self.rel,
            "dst": self.dst,
            "dst_type": self.dst_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


def validate_triple(t: Triple, strict: bool = True) -> bool:
    """Validate a triple against strict entity types, relation types, and edge signatures."""
    src_type = t.src_type.upper().strip()
    dst_type = t.dst_type.upper().strip()
    rel = t.rel.upper().strip()

    if src_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity type for src: '{src_type}'. Allowed: {sorted(ENTITY_TYPES)}")

    if dst_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity type for dst: '{dst_type}'. Allowed: {sorted(ENTITY_TYPES)}")

    if rel not in RELATION_TYPES:
        raise ValidationError(f"Invalid relation type: '{rel}'. Allowed: {sorted(RELATION_TYPES)}")

    sig = (src_type, rel, dst_type)
    if strict and sig not in ALLOWED_SIGNATURES:
        raise ValidationError(f"Invalid edge signature '{sig}'. Not in ALLOWED_SIGNATURES.")

    return True
