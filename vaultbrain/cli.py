"""Vault Brain CLI for indexing, querying, and analyzing the Obsidian knowledge graph."""

from __future__ import annotations

import argparse
import sys
import os
import time
import json
from typing import Dict, Any

from vaultbrain.parser import parse_vault
from vaultbrain.extractor import extract_graph_from_notes
from vaultbrain.graph import VaultGraph


def build_index(vault_path: str, db_path: str, quiet: bool = False) -> Dict[str, Any]:
    start_time = time.time()

    if not os.path.exists(vault_path):
        raise FileNotFoundError(f"Vault directory not found: {vault_path}")

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    if not quiet:
        print(f"[*] Scanning Obsidian vault: {vault_path}")

    notes = parse_vault(vault_path)
    parse_duration = time.time() - start_time

    if not quiet:
        print(f"[*] Parsed {len(notes)} notes in {parse_duration:.2f}s")
        print("[*] Extracting entities and knowledge graph relations...")

    extract_start = time.time()
    vg = extract_graph_from_notes(notes)
    extract_duration = time.time() - extract_start

    vg.save_to_sqlite(db_path)
    total_duration = time.time() - start_time

    st = vg.stats()

    # Find top hubs (highest degree)
    degree_sorted = sorted(vg.g.degree(), key=lambda x: x[1], reverse=True)[:10]

    # Find orphan notes (0 degree)
    orphans = [n for n, deg in vg.g.degree() if deg == 0 and vg.g.nodes[n].get("source_file")]

    # Find missing links (nodes referenced with no source_file)
    missing_links = [n for n, d in vg.g.nodes(data=True) if not d.get("source_file")]

    summary = {
        "vault_path": vault_path,
        "db_path": db_path,
        "notes_count": len(notes),
        "nodes_count": st["nodes_count"],
        "edges_count": st["edges_count"],
        "node_types": st["node_types"],
        "relations": st["relations"],
        "top_hubs": [{"node": node, "degree": deg} for node, deg in degree_sorted],
        "orphans_count": len(orphans),
        "missing_links_count": len(missing_links),
        "duration_seconds": round(total_duration, 2),
    }

    if not quiet:
        print("\n" + "=" * 50)
        print("  🧠 VAULT BRAIN KNOWLEDGE GRAPH INDEXED")
        print("=" * 50)
        print(f"  Notes Parsed   : {len(notes)}")
        print(f"  Graph Nodes    : {st['nodes_count']}")
        print(f"  Graph Edges    : {st['edges_count']}")
        print(f"  Orphan Notes   : {len(orphans)}")
        print(f"  Missing Links  : {len(missing_links)}")
        print(f"  Total Duration : {total_duration:.2f}s")
        print("-" * 50)
        print("  Top Connected Hubs:")
        for hub in degree_sorted[:5]:
            print(f"    - {hub[0]} ({hub[1]} connections)")
        print("=" * 50)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Vault Brain CLI")
    subparsers = parser.add_subparsers(dest="command")

    # index command
    idx_parser = subparsers.add_parser("index", help="Index vault into SQLite graph DB")
    idx_parser.add_argument("--vault", default="/root/obsidian-vault", help="Path to Obsidian vault")
    idx_parser.add_argument("--out", default="/root/vaultbrain/vault.db", help="Path to output SQLite DB")
    idx_parser.add_argument("--json", action="store_true", help="Output summary as JSON")
    idx_parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    # query command
    q_parser = subparsers.add_parser("query", help="Query neighbors, paths, or subgraph")
    q_parser.add_argument("query_text", help="Query text or node name to search")
    q_parser.add_argument("--db", default="/root/vaultbrain/vault.db", help="Path to SQLite DB")
    q_parser.add_argument("--hops", type=int, default=1, help="Hop distance (default: 1)")
    q_parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")

    # trace command
    t_parser = subparsers.add_parser("trace", help="Trace a topic evolution and connections")
    t_parser.add_argument("topic", help="Topic to trace")
    t_parser.add_argument("--db", default="/root/vaultbrain/vault.db", help="Path to SQLite DB")

    # path command
    p_parser = subparsers.add_parser("path", help="Find path between two nodes")
    p_parser.add_argument("src", help="Source node")
    p_parser.add_argument("dst", help="Destination node")
    p_parser.add_argument("--db", default="/root/vaultbrain/vault.db", help="Path to SQLite DB")
    p_parser.add_argument("--max-hops", type=int, default=3, help="Max hops (default: 3)")

    args = parser.parse_args()

    if args.command == "index":
        is_quiet = args.quiet or args.json
        summary = build_index(args.vault, args.out, quiet=is_quiet)
        if args.json:
            print(json.dumps(summary, indent=2))
    elif args.command == "query":
        from vaultbrain.retrieval import GraphRetriever
        vg = VaultGraph.load_from_sqlite(args.db)
        retriever = GraphRetriever(vg)
        if args.format == "json":
            res = retriever.query_graph(args.query_text)
            print(json.dumps(res, indent=2))
        else:
            print(retriever.render_markdown_answer(args.query_text))
    elif args.command == "trace":
        from vaultbrain.retrieval import GraphRetriever
        vg = VaultGraph.load_from_sqlite(args.db)
        retriever = GraphRetriever(vg)
        timeline = retriever.trace_topic(args.topic)
        print(f"[*] Topic Trace: '{args.topic}' ({len(timeline)} relevant nodes)")
        for item in timeline:
            print(f"  - [{item['type']}] {item['id']} -> {item['source_file']} (in:{item['in_degree']}, out:{item['out_degree']})")
    elif args.command == "path":
        vg = VaultGraph.load_from_sqlite(args.db)
        paths = vg.find_paths(args.src, args.dst, max_hops=args.max_hops)
        print(f"[*] Paths from '{args.src}' to '{args.dst}': {len(paths)}")
        for p in paths:
            print("  -> " + " -> ".join(p))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
