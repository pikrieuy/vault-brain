import os
import pytest
from vaultbrain.graph import VaultGraph
from vaultbrain.ontology import Triple

def test_graph_add_nodes_and_edges(tmp_path):
    vg = VaultGraph()

    vg.add_node("Beemate", "PROJECT", "Beemate Project", source_file="50-Projects/Beemate.md")
    vg.add_node("FastAPI", "TOOL", "FastAPI Framework")
    vg.add_node("GraphRAG", "CONCEPT", "Graph Retrieval")

    vg.add_edge("Beemate", "FastAPI", "DEPENDS_ON", confidence=1.0, evidence="Requirements")
    vg.add_edge("Beemate", "GraphRAG", "IMPLEMENTS", confidence=0.9, evidence="Doc")

    st = vg.stats()
    assert st["nodes_count"] == 3
    assert st["edges_count"] == 2
    assert st["node_types"]["PROJECT"] == 1
    assert st["node_types"]["TOOL"] == 1
    assert st["relations"]["DEPENDS_ON"] == 1

    # SQLite round-trip
    db_file = str(tmp_path / "test_graph.db")
    vg.save_to_sqlite(db_file)
    assert os.path.exists(db_file)

    vg_loaded = VaultGraph.load_from_sqlite(db_file)
    assert vg_loaded.stats()["nodes_count"] == 3
    assert vg_loaded.stats()["edges_count"] == 2

def test_graph_traversal():
    vg = VaultGraph()
    vg.add_node("Pikri", "PERSON", "Pikri")
    vg.add_node("Beemate", "PROJECT", "Beemate")
    vg.add_node("FastAPI", "TOOL", "FastAPI")

    vg.add_edge("Pikri", "Beemate", "OWNS")
    vg.add_edge("Beemate", "FastAPI", "DEPENDS_ON")

    # Neighbors 1 hop
    n1 = vg.get_neighbors("Pikri", hops=1)
    assert "Beemate" in [n["id"] for n in n1]
    assert "FastAPI" not in [n["id"] for n in n1]

    # Neighbors 2 hops
    n2 = vg.get_neighbors("Pikri", hops=2)
    ids2 = [n["id"] for n in n2]
    assert "Beemate" in ids2
    assert "FastAPI" in ids2

    # Find path
    paths = vg.find_paths("Pikri", "FastAPI", max_hops=3)
    assert len(paths) == 1
    assert paths[0] == ["Pikri", "Beemate", "FastAPI"]
