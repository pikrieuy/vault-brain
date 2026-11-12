"""Graph-augmented retrieval engine for Vault Brain."""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional
from vaultbrain.graph import VaultGraph


class GraphRetriever:
    def __init__(self, graph: VaultGraph):
        self.vg = graph

    def find_related(self, node_id: str, hops: int = 2) -> List[Dict[str, Any]]:
        """Find related nodes within N hops along with relation details."""
        neighbors = self.vg.get_neighbors(node_id, hops=hops)
        results = []

        # Gather incoming & outgoing edges for connected nodes
        for n in neighbors:
            nid = n["id"]
            direct_edges = []

            # Check direct connections to query node or between neighbors
            if self.vg.g.has_edge(node_id, nid):
                edata = self.vg.g.get_edge_data(node_id, nid)
                direct_edges.append({
                    "direction": "out",
                    "rel": edata.get("rel", "RELATES_TO"),
                    "evidence": edata.get("evidence", "")
                })
            if self.vg.g.has_edge(nid, node_id):
                edata = self.vg.g.get_edge_data(nid, node_id)
                direct_edges.append({
                    "direction": "in",
                    "rel": edata.get("rel", "RELATES_TO"),
                    "evidence": edata.get("evidence", "")
                })

            n["connections"] = direct_edges
            results.append(n)

        return results

    def query_graph(self, query: str, max_nodes: int = 10) -> Dict[str, Any]:
        """Search nodes by substring/token match and expand their local subgraph."""
        q_tokens = [tok.lower() for tok in re.split(r"\W+", query) if tok]
        if not q_tokens:
            return {"matched_nodes": [], "subgraph": {"nodes": [], "edges": []}}

        scored_nodes = []
        for n, data in self.vg.g.nodes(data=True):
            n_lower = n.lower()
            label_lower = data.get("label", "").lower()
            score = 0

            for tok in q_tokens:
                if tok == n_lower:
                    score += 10
                elif tok in n_lower:
                    score += 5
                elif tok in label_lower:
                    score += 3

            if score > 0:
                scored_nodes.append((score, n))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        top_matches = [node for _, node in scored_nodes[:max_nodes]]

        # Build subgraph
        subgraph_nodes = set(top_matches)
        for m in top_matches:
            for neighbor in self.vg.g.neighbors(m):
                subgraph_nodes.add(neighbor)
            for predecessor in self.vg.g.predecessors(m):
                subgraph_nodes.add(predecessor)

        nodes_data = []
        for sn in sorted(subgraph_nodes):
            nd = self.vg.g.nodes[sn]
            nodes_data.append({
                "id": sn,
                "type": nd.get("type", "NOTE"),
                "label": nd.get("label", sn),
                "source_file": nd.get("source_file", "")
            })

        edges_data = []
        for u in subgraph_nodes:
            for v in self.vg.g.successors(u):
                if v in subgraph_nodes:
                    ed = self.vg.g.get_edge_data(u, v)
                    edges_data.append({
                        "src": u,
                        "dst": v,
                        "rel": ed.get("rel", "RELATES_TO"),
                        "evidence": ed.get("evidence", "")
                    })

        return {
            "query": query,
            "matched_nodes": top_matches,
            "subgraph": {
                "nodes": nodes_data,
                "edges": edges_data
            }
        }

    def trace_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Trace topic connections and chronological appearances across the vault."""
        res = self.query_graph(topic, max_nodes=5)
        matched = res["matched_nodes"]
        timeline = []

        for m in matched:
            data = self.vg.g.nodes[m]
            timeline.append({
                "id": m,
                "type": data.get("type", "NOTE"),
                "label": data.get("label", m),
                "source_file": data.get("source_file", ""),
                "in_degree": self.vg.g.in_degree(m),
                "out_degree": self.vg.g.out_degree(m),
            })

        return timeline

    def render_markdown_answer(self, query: str) -> str:
        """Render a formatted markdown response for a query."""
        res = self.query_graph(query)
        matches = res["matched_nodes"]
        if not matches:
            return f"❌ Tidak ditemukan relasi knowledge graph untuk query: `{query}`"

        lines = [
            f"### 🧠 Vault Brain: Hasil Graph untuk `{query}`\n",
            f"**Node Utama Ditemukan:** {', '.join(f'`{m}`' for m in matches)}\n",
            "#### 🔗 Relasi & Konektivitas Subgraph:"
        ]

        edges = res["subgraph"]["edges"]
        if not edges:
            lines.append("*(Tidak ada edge/koneksi langsung ke node lain)*")
        else:
            for e in edges[:15]:
                ev_str = f" _(\"{e['evidence']}\")_" if e["evidence"] else ""
                lines.append(f"- **{e['src']}** `-{e['rel']}->` **{e['dst']}**{ev_str}")

        lines.append("\n#### 📂 File Sumber Referensi:")
        for n in res["subgraph"]["nodes"][:8]:
            if n["source_file"]:
                lines.append(f"- `[[{n['id']}]]` ({n['type']}) → `{n['source_file']}`")

        return "\n".join(lines)
