"""VaultGraph: In-memory NetworkX directed graph with SQLite persistence."""

from __future__ import annotations

import sqlite3
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple


class VaultGraph:
    def __init__(self):
        self.g: nx.DiGraph = nx.DiGraph()

    def add_node(self, node_id: str, node_type: str, label: str = "", source_file: Optional[str] = None):
        clean_id = node_id.strip()
        if not clean_id:
            return
        # If node already exists, update attributes without overwriting valid data with empty data
        if self.g.has_node(clean_id):
            curr = self.g.nodes[clean_id]
            if not curr.get("label") and label:
                curr["label"] = label
            if not curr.get("source_file") and source_file:
                curr["source_file"] = source_file
            if curr.get("type") == "NOTE" and node_type != "NOTE":
                curr["type"] = node_type
        else:
            self.g.add_node(
                clean_id,
                type=node_type.upper().strip(),
                label=label.strip() if label else clean_id,
                source_file=source_file or ""
            )

    def add_edge(self, src: str, dst: str, rel: str, confidence: float = 1.0, evidence: str = ""):
        clean_src = src.strip()
        clean_dst = dst.strip()
        if not clean_src or not clean_dst or clean_src == clean_dst:
            return

        # Ensure nodes exist
        if not self.g.has_node(clean_src):
            self.add_node(clean_src, "NOTE", clean_src)
        if not self.g.has_node(clean_dst):
            self.add_node(clean_dst, "NOTE", clean_dst)

        self.g.add_edge(
            clean_src,
            clean_dst,
            rel=rel.upper().strip(),
            confidence=float(confidence),
            evidence=evidence.strip()
        )

    def stats(self) -> Dict[str, Any]:
        node_types = {}
        for _, data in self.g.nodes(data=True):
            t = data.get("type", "UNKNOWN")
            node_types[t] = node_types.get(t, 0) + 1

        relations = {}
        for _, _, data in self.g.edges(data=True):
            r = data.get("rel", "UNKNOWN")
            relations[r] = relations.get(r, 0) + 1

        return {
            "nodes_count": self.g.number_of_nodes(),
            "edges_count": self.g.number_of_edges(),
            "node_types": node_types,
            "relations": relations,
        }

    def get_neighbors(self, node_id: str, hops: int = 1) -> List[Dict[str, Any]]:
        clean_id = node_id.strip()
        if not self.g.has_node(clean_id):
            return []

        # Undirected traversal for semantic discovery (in & out edges)
        undirected = self.g.to_undirected(as_view=True)
        lengths = nx.single_source_shortest_path_length(undirected, clean_id, cutoff=hops)

        results = []
        for n, dist in lengths.items():
            if n == clean_id:
                continue
            data = self.g.nodes[n]
            results.append({
                "id": n,
                "type": data.get("type", "UNKNOWN"),
                "label": data.get("label", n),
                "distance": dist,
                "source_file": data.get("source_file", "")
            })
        return sorted(results, key=lambda x: (x["distance"], x["id"]))

    def find_paths(self, src: str, dst: str, max_hops: int = 3) -> List[List[str]]:
        clean_src = src.strip()
        clean_dst = dst.strip()
        if not self.g.has_node(clean_src) or not self.g.has_node(clean_dst):
            return []

        undirected = self.g.to_undirected(as_view=True)
        try:
            paths = list(nx.all_simple_paths(undirected, clean_src, clean_dst, cutoff=max_hops))
            return sorted(paths, key=len)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def save_to_sqlite(self, db_path: str):
        conn = sqlite3.connect(db_path, timeout=30.0)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA busy_timeout=30000;")

        cur.execute("DROP TABLE IF EXISTS edges;")
        cur.execute("DROP TABLE IF EXISTS nodes;")

        cur.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                label TEXT,
                source_file TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE edges (
                src TEXT,
                dst TEXT,
                rel TEXT,
                confidence REAL,
                evidence TEXT
            );
        """)

        cur.execute("CREATE INDEX idx_edges_src ON edges(src);")
        cur.execute("CREATE INDEX idx_edges_dst ON edges(dst);")

        node_rows = [
            (n, data.get("type", "NOTE"), data.get("label", n), data.get("source_file", ""))
            for n, data in self.g.nodes(data=True)
        ]
        cur.executemany("INSERT INTO nodes (id, type, label, source_file) VALUES (?, ?, ?, ?);", node_rows)

        edge_rows = [
            (u, v, data.get("rel", "RELATES_TO"), data.get("confidence", 1.0), data.get("evidence", ""))
            for u, v, data in self.g.edges(data=True)
        ]
        cur.executemany("INSERT INTO edges (src, dst, rel, confidence, evidence) VALUES (?, ?, ?, ?, ?);", edge_rows)

        conn.commit()
        conn.close()

    @classmethod
    def load_from_sqlite(cls, db_path: str) -> VaultGraph:
        vg = cls()
        conn = sqlite3.connect(db_path, timeout=30.0)
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000;")

        cur.execute("SELECT id, type, label, source_file FROM nodes;")
        for node_id, node_type, label, source_file in cur.fetchall():
            vg.add_node(node_id, node_type, label, source_file)

        cur.execute("SELECT src, dst, rel, confidence, evidence FROM edges;")
        for src, dst, rel, confidence, evidence in cur.fetchall():
            vg.add_edge(src, dst, rel, confidence, evidence)

        conn.close()
        return vg
