"""FastMCP server for Vault Brain knowledge graph."""

from __future__ import annotations

import os
import json
from mcp.server.fastmcp import FastMCP
from vaultbrain.graph import VaultGraph
from vaultbrain.retrieval import GraphRetriever

DEFAULT_DB_PATH = os.environ.get("VAULTBRAIN_DB", "/root/vaultbrain/vault.db")

mcp = FastMCP("vaultbrain")


def _get_retriever(db_path: str = DEFAULT_DB_PATH) -> GraphRetriever:
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Vault Brain database not found at {db_path}. Please run `vaultbrain index` first."
        )
    vg = VaultGraph.load_from_sqlite(db_path)
    return GraphRetriever(vg)


@mcp.tool()
def query_graph(query: str) -> str:
    """Query the Obsidian knowledge graph for entities, connections, and source notes matching a concept or keyword."""
    retriever = _get_retriever()
    return retriever.render_markdown_answer(query)


@mcp.tool()
def find_related(node_id: str, hops: int = 1) -> str:
    """Find related notes and concepts within 1 or 2 hops from a given note in the Obsidian vault."""
    retriever = _get_retriever()
    related = retriever.find_related(node_id, hops=hops)
    if not related:
        return f"Tidak ditemukan node terhubung untuk `{node_id}`."

    lines = [f"### 🔗 Related Nodes for `{node_id}` (hops={hops}):\n"]
    for r in related:
        conn_str = ""
        if r.get("connections"):
            conns = [f"{c['direction']} ({c['rel']})" for c in r["connections"]]
            conn_str = f" [koneksi: {', '.join(conns)}]"
        lines.append(f"- **{r['id']}** ({r['type']}) - jarak: {r['distance']}{conn_str}")
        if r.get("source_file"):
            lines.append(f"  └─ File: `{r['source_file']}`")

    return "\n".join(lines)


@mcp.tool()
def trace_topic(topic: str) -> str:
    """Trace the chronological evolution, degree of connections, and central notes for a topic across the Obsidian vault."""
    retriever = _get_retriever()
    timeline = retriever.trace_topic(topic)
    if not timeline:
        return f"Tidak ditemukan topik atau catatan terkait: `{topic}`."

    lines = [f"### ⏳ Topic Trace: `{topic}` ({len(timeline)} catatan relevan):\n"]
    for t in timeline:
        lines.append(f"- **{t['id']}** ({t['type']}) | In-degree: {t['in_degree']}, Out-degree: {t['out_degree']}")
        if t.get("source_file"):
            lines.append(f"  └─ `{t['source_file']}`")

    return "\n".join(lines)


@mcp.tool()
def vault_hubs(top_n: int = 10) -> str:
    """List the most central and connected knowledge hubs across the entire Obsidian vault."""
    retriever = _get_retriever()
    degree_sorted = sorted(retriever.vg.g.degree(), key=lambda x: x[1], reverse=True)[:top_n]

    lines = [f"### 🏛️ Top {top_n} Vault Knowledge Hubs:\n"]
    for node, deg in degree_sorted:
        data = retriever.vg.g.nodes[node]
        src = f" (`{data.get('source_file')}`)" if data.get('source_file') else " *(virtual/external)*"
        lines.append(f"- **{node}** ({data.get('type', 'NOTE')}) : **{deg}** koneksi{src}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
