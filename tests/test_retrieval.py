import os
import pytest
from vaultbrain.graph import VaultGraph
from vaultbrain.retrieval import GraphRetriever

def test_graph_retrieval(tmp_path):
    vg = VaultGraph()
    vg.add_node("Pikri", "PERSON", "Pikri", source_file="60-Agents/Pikri.md")
    vg.add_node("Beemate", "PROJECT", "Beemate", source_file="50-Projects/Beemate.md")
    vg.add_node("FastAPI", "TOOL", "FastAPI", source_file="70-Tools/FastAPI.md")
    vg.add_node("GraphRAG", "CONCEPT", "GraphRAG Architecture", source_file="80-Learn/GraphRAG.md")

    vg.add_edge("Pikri", "Beemate", "OWNS", evidence="Pikri is creator")
    vg.add_edge("Beemate", "FastAPI", "DEPENDS_ON", evidence="built with FastAPI")
    vg.add_edge("Beemate", "GraphRAG", "IMPLEMENTS", evidence="implements GraphRAG")

    retriever = GraphRetriever(vg)

    # 1. find_related
    related = retriever.find_related("Beemate", hops=1)
    related_ids = [r["id"] for r in related]
    assert "Pikri" in related_ids
    assert "FastAPI" in related_ids
    assert "GraphRAG" in related_ids

    # 2. query_graph
    res = retriever.query_graph("FastAPI")
    assert "FastAPI" in res["matched_nodes"]
    assert len(res["subgraph"]["edges"]) >= 1

    # 3. trace_topic
    trace = retriever.trace_topic("Beemate")
    assert len(trace) >= 1
    assert trace[0]["id"] == "Beemate"
