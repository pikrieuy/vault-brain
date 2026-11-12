import os
import pytest
from vaultbrain.parser import parse_vault
from vaultbrain.extractor import extract_graph_from_notes
from vaultbrain.graph import VaultGraph

def test_extract_graph_from_mini_vault():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "mini-vault")
    notes = parse_vault(fixtures_dir)

    vg = extract_graph_from_notes(notes)
    st = vg.stats()

    # Should have nodes for Note-A, Note-B, Note-C, plus linked external entities like FastAPI, Pikri, NoSuchNote
    assert st["nodes_count"] >= 5
    assert st["edges_count"] >= 3

    # Check Note-A (concept) and Note-B (project)
    node_a = vg.g.nodes["Note-A"]
    assert node_a["type"] == "CONCEPT"

    node_b = vg.g.nodes["Note-B"]
    assert node_b["type"] == "PROJECT"

    # Check relation between Note-B and Note-A
    # Note-B mentions Note-A (concept) -> IMPLEMENTS or RELATES_TO
    assert vg.g.has_edge("Note-B", "Note-A")
    edge_data = vg.g.get_edge_data("Note-B", "Note-A")
    assert edge_data["rel"] in ["IMPLEMENTS", "RELATES_TO"]
