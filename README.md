# Vault Brain 🧠

> High-performance GraphRAG knowledge graph retrieval engine for Obsidian Vaults.
> Built for Hermes Agent & Vickry's personal second brain.

## Features
- **Deterministic Obsidian Parser:** Fast regex & AST extraction of YAML frontmatter, wikilinks (`[[Note#Section|Alias]]`), headings, and tags.
- **Strict Ontology:** Enforces verified entity types (`NOTE`, `CONCEPT`, `PROJECT`, `TOOL`, `PERSON`) and relations (`RELATES_TO`, `DEPENDS_ON`, `IMPLEMENTS`, `PART_OF`, `OWNS`, `MENTIONED_IN`).
- **In-Memory NetworkX + SQLite Persistence:** Lightning-fast graph traversal and pathfinding (<50ms) backed by persistent disk storage (`vault.db`).
- **GraphRAG Semantic Retrieval:** Multi-hop semantic traversal and context-aware evidence snippet extraction.
- **Native MCP Server:** Exposes `query_graph`, `find_related`, `trace_topic`, and `vault_hubs` directly to Hermes and Claude Code.
- **Zero Heavy External Dependencies:** Pure Python (`networkx`, `pyyaml`, `mcp`), RAM footprint < 80MB.

## CLI Usage

```bash
# Index Obsidian vault
vaultbrain index --vault /root/obsidian-vault --out /root/vaultbrain/vault.db

# Query graph for a concept or keyword
vaultbrain query "FastAPI"

# Trace topic evolution across notes
vaultbrain trace "Beemate"

# Find paths between two notes
vaultbrain path "Pikri" "FastAPI" --max-hops 3
```

## Running Tests

```bash
cd /root/vaultbrain
/usr/local/lib/hermes-agent/venv/bin/pytest tests/ -v
```
