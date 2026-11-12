import os
import pytest
from vaultbrain.parser import parse_vault, parse_markdown_file, Note

def test_parse_single_note():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "mini-vault")
    note_a_path = os.path.join(fixtures_dir, "Note-A.md")

    note = parse_markdown_file(note_a_path, fixtures_dir)
    assert note.title == "Note-A"
    assert "concept" in note.tags
    assert "ai" in note.tags
    assert "Graph Retrieval" in note.aliases
    assert note.frontmatter.get("date") == "2026-11-01"

    # Wikilinks extracted and normalized
    targets = [link["target"] for link in note.wikilinks]
    assert "Note-B" in targets
    assert "Note-C" in targets
    assert "NoSuchNote" in targets

    # Alias preserved in link metadata, but target is clean note name
    link_b = next(l for l in note.wikilinks if l["target"] == "Note-B")
    assert link_b["alias"] == "Concept B"

    # Section extracted
    link_c = next(l for l in note.wikilinks if l["target"] == "Note-C")
    assert link_c["section"] == "Implementation"

def test_parse_vault_directory():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "mini-vault")
    notes = parse_vault(fixtures_dir)

    assert len(notes) == 3
    titles = {n.title for n in notes}
    assert titles == {"Note-A", "Note-B", "Note-C"}
