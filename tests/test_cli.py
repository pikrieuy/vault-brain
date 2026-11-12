import os
import subprocess
import json

def test_cli_indexing_and_querying(tmp_path):
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "mini-vault")
    db_file = str(tmp_path / "mini.db")

    # 1. Test indexing
    cmd_index = [
        "/usr/local/lib/hermes-agent/venv/bin/python",
        "-m", "vaultbrain.cli",
        "index",
        "--vault", fixtures_dir,
        "--out", db_file,
        "--json"
    ]
    res = subprocess.run(cmd_index, capture_output=True, text=True, cwd="/root/vaultbrain")
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["notes_count"] == 3
    assert data["nodes_count"] >= 5
    assert os.path.exists(db_file)

    # 2. Test query
    cmd_query = [
        "/usr/local/lib/hermes-agent/venv/bin/python",
        "-m", "vaultbrain.cli",
        "query",
        "Note-A",
        "--db", db_file,
        "--hops", "1"
    ]
    res_q = subprocess.run(cmd_query, capture_output=True, text=True, cwd="/root/vaultbrain")
    assert res_q.returncode == 0
    assert "Note-B" in res_q.stdout or "Note-C" in res_q.stdout
