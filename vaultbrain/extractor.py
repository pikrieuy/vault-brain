"""Extracts knowledge graph entities and relations from parsed notes using heuristics and ontology."""

from __future__ import annotations

import re
from typing import List, Dict, Optional, Tuple
from vaultbrain.parser import Note
from vaultbrain.graph import VaultGraph
from vaultbrain.ontology import validate_triple, Triple, ValidationError, ALLOWED_SIGNATURES

# Folder-to-type heuristics
FOLDER_TYPE_MAP = {
    "00-Meta": "NOTE",
    "10-Content": "NOTE",
    "20-Clients": "PERSON",
    "30-Business": "PROJECT",
    "40-Finance": "NOTE",
    "50-Projects": "PROJECT",
    "60-Agents": "PERSON",
    "70-Tools": "TOOL",
    "80-Learn": "CONCEPT",
    "90-Journal": "NOTE",
    "91-Knowledge": "CONCEPT",
}

# Tag-to-type heuristics
TAG_TYPE_MAP = {
    "project": "PROJECT",
    "tool": "TOOL",
    "tools": "TOOL",
    "concept": "CONCEPT",
    "learn": "CONCEPT",
    "person": "PERSON",
    "agent": "PERSON",
}


def infer_entity_type(note: Note) -> str:
    """Infer entity type from tags, folder path, or default to NOTE."""
    # 1. Tags match
    for t in note.tags:
        t_lower = t.lower()
        if t_lower in TAG_TYPE_MAP:
            return TAG_TYPE_MAP[t_lower]

    # 2. Path prefix match
    norm_path = note.rel_path.replace("\\", "/")
    for folder, etype in FOLDER_TYPE_MAP.items():
        if norm_path.startswith(folder):
            return etype

    return "NOTE"


def extract_context_sentence(content: str, target: str) -> str:
    """Extract the sentence containing the wikilink target as evidence."""
    escaped = re.escape(target)
    # Match sentence containing [[target...]]
    pattern = rf"([^.?!;\n]*\[\[{escaped}[^\]]*\]\][^.?!;\n]*)"
    m = re.search(pattern, content, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def infer_relation(src_type: str, dst_type: str, context: str) -> str:
    """Infer relation based on types and context keywords."""
    ctx_lower = context.lower()

    if "depend" in ctx_lower or "butuh" in ctx_lower or "stack" in ctx_lower:
        if (src_type, "DEPENDS_ON", dst_type) in ALLOWED_SIGNATURES:
            return "DEPENDS_ON"

    if "implement" in ctx_lower or "terapin" in ctx_lower or "pakai" in ctx_lower:
        if (src_type, "IMPLEMENTS", dst_type) in ALLOWED_SIGNATURES:
            return "IMPLEMENTS"

    if "owner" in ctx_lower or "owned by" in ctx_lower or "milik" in ctx_lower or "punya" in ctx_lower:
        if (src_type, "OWNS", dst_type) in ALLOWED_SIGNATURES:
            return "OWNS"

    # Default mappings based on type signatures
    if src_type == "PROJECT" and dst_type == "TOOL":
        return "DEPENDS_ON"
    if src_type == "PROJECT" and dst_type == "CONCEPT":
        return "IMPLEMENTS"
    if src_type == "PERSON" and dst_type == "PROJECT":
        return "OWNS"
    if (src_type, "RELATES_TO", dst_type) in ALLOWED_SIGNATURES:
        return "RELATES_TO"

    return "RELATES_TO"


def extract_graph_from_notes(notes: List[Note]) -> VaultGraph:
    """Build a VaultGraph from a list of parsed notes."""
    vg = VaultGraph()

    # Index notes by title & aliases
    note_by_title: Dict[str, Note] = {}
    note_types: Dict[str, str] = {}

    for note in notes:
        etype = infer_entity_type(note)
        note_by_title[note.title] = note
        note_types[note.title] = etype
        vg.add_node(note.title, etype, label=note.title, source_file=note.rel_path)

        for alias in note.aliases:
            if alias:
                note_by_title[alias] = note
                note_types[alias] = etype

    # Second pass: Process wikilinks and relations
    for note in notes:
        src_id = note.title
        src_type = note_types.get(src_id, "NOTE")

        for link in note.wikilinks:
            target_id = link["target"]
            if not target_id:
                continue

            # Determine target type
            dst_type = note_types.get(target_id)
            if not dst_type:
                # Target note not in parsed notes (external reference or missing note)
                dst_type = "NOTE"

            context_evidence = extract_context_sentence(note.raw_content, target_id)
            rel = infer_relation(src_type, dst_type, context_evidence)

            # Validate triple or fallback to safe signature
            try:
                triple = Triple(
                    src=src_id,
                    src_type=src_type,
                    rel=rel,
                    dst=target_id,
                    dst_type=dst_type,
                    confidence=1.0,
                    evidence=context_evidence
                )
                validate_triple(triple, strict=True)
                final_rel = rel
            except ValidationError:
                final_rel = "RELATES_TO"

            vg.add_edge(src_id, target_id, final_rel, confidence=1.0, evidence=context_evidence)

    return vg
