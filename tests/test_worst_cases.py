import os
import pytest
from vaultbrain.parser import parse_markdown_file
from vaultbrain.graph import VaultGraph
from vaultbrain.retrieval import GraphRetriever
from vaultbrain.extractor import extract_context_sentence, infer_relation

def test_vaultbrain_malformed_yaml(tmp_path):
    note_file = tmp_path / "bad_yaml.md"
    note_file.write_text("""---
this is: [unclosed list
invalid: yaml: here
---
# Title
Some content
""")
    # Parser must not crash on invalid YAML
    note = parse_markdown_file(str(note_file), str(tmp_path))
    assert note.title == "bad_yaml"
    assert note.frontmatter == {}

def test_vaultbrain_yaml_list_or_scalar(tmp_path):
    note_file = tmp_path / "scalar_yaml.md"
    note_file.write_text("""---
- item 1
- item 2
---
# Just a list
""")
    note = parse_markdown_file(str(note_file), str(tmp_path))
    assert note.frontmatter == {}

def test_vaultbrain_weird_and_malformed_wikilinks(tmp_path):
    note_file = tmp_path / "links.md"
    note_file.write_text("""# Links Test
[[]]
[[ ]]
[[|]]
[[#]]
[[#OnlySection]]
[[Note|]]
[[|OnlyAlias]]
[[Note#]]
[[../../outside/secret]]
[[Normal Note#Section|Alias Name]]
""")
    note = parse_markdown_file(str(note_file), str(tmp_path))
    targets = [l["target"] for l in note.wikilinks]
    # Traversal characters ../ should be sanitized or stripped
    assert "" not in targets
    assert "Normal Note" in targets

def test_vaultbrain_query_with_regex_special_characters():
    vg = VaultGraph()
    vg.add_node("C++", "TOOL", "C++ Programming")
    vg.add_node("Regex (v2)", "CONCEPT", "Regex patterns [v2]")
    vg.add_edge("C++", "Regex (v2)", "RELATES_TO")

    retriever = GraphRetriever(vg)
    # Queries containing regex metacharacters: +, *, [, ], (, ), ?, ^, $
    res1 = retriever.query_graph("C++")
    assert isinstance(res1, dict)

    res2 = retriever.query_graph("[v2] (advanced)? *test*")
    assert isinstance(res2, dict)

    md = retriever.render_markdown_answer("C++ [test]*?")
    assert isinstance(md, str)

def test_vaultbrain_graph_cycles_and_infinite_loops():
    vg = VaultGraph()
    # Circular graph: A -> B -> C -> A
    vg.add_node("A", "NOTE")
    vg.add_node("B", "NOTE")
    vg.add_node("C", "NOTE")
    vg.add_edge("A", "B", "RELATES_TO")
    vg.add_edge("B", "C", "RELATES_TO")
    vg.add_edge("C", "A", "RELATES_TO")

    # Shortest paths must terminate
    paths = vg.find_paths("A", "C", max_hops=5)
    assert len(paths) >= 1

    retriever = GraphRetriever(vg)
    related = retriever.find_related("A", hops=3)
    assert len(related) == 2  # B and C

def test_vaultbrain_nonexistent_nodes():
    vg = VaultGraph()
    vg.add_node("A", "NOTE")

    retriever = GraphRetriever(vg)
    assert retriever.find_related("DOES_NOT_EXIST") == []
    assert retriever.trace_topic("DOES_NOT_EXIST") == []
    assert vg.find_paths("DOES_NOT_EXIST", "A") == []
    assert vg.find_paths("A", "DOES_NOT_EXIST") == []
