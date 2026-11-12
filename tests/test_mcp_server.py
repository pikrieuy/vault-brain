import os
import pytest
from vaultbrain.mcp_server import query_graph, find_related, trace_topic, vault_hubs

def test_mcp_server_tools():
    # Test using live /root/vaultbrain/vault.db
    if not os.path.exists("/root/vaultbrain/vault.db"):
        pytest.skip("vault.db not built yet")

    hubs_res = vault_hubs(top_n=5)
    assert "Top 5 Vault Knowledge Hubs" in hubs_res
    assert "koneksi" in hubs_res

    query_res = query_graph("Beemate")
    assert "Vault Brain: Hasil Graph untuk" in query_res

    trace_res = trace_topic("Beemate")
    assert "Topic Trace" in trace_res
