"""Tests for AI-KOS MCP server — tool listing and tool calling."""

import asyncio, json, pytest


async def _mcp_request(proc, method: str, params: dict | None = None, msg_id: int = 1):
    """Send a JSON-RPC request and read the response line."""
    msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        msg["params"] = params
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    await proc.stdin.drain()
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
    return json.loads(line.decode())


async def _start_server():
    """Start the MCP server as a subprocess and complete initialization."""
    proc = await asyncio.create_subprocess_exec(
        "python3", "-m", "ai_kos.mcp_server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=2**20,  # 1MB buffer — large enough for 71+ article listings
    )
    # Initialize
    await _mcp_request(proc, "initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    })
    # Send initialized notification
    proc.stdin.write((json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode())
    await proc.stdin.drain()
    await asyncio.sleep(0.2)
    return proc


@pytest.mark.asyncio
async def test_list_tools():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/list", {}, msg_id=2)
        assert "result" in resp, f"Expected result, got: {resp}"
        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}

        expected = {
            "ai_kos_ingest", "ai_kos_create", "ai_kos_search",
            "ai_kos_read", "ai_kos_link", "ai_kos_list",
            "ai_kos_merge_candidates", "ai_kos_templates",
            "ai_kos_graph", "ai_kos_compare", "ai_kos_stats",
            "ai_kos_clean", "ai_kos_research_plan", "ai_kos_research_persist",
            "ai_kos_migrate",
        }
        assert tool_names == expected, f"Missing tools: {expected - tool_names}"
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_stats():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_stats",
            "arguments": {},
        }, msg_id=3)
        assert "result" in resp, f"Error: {resp.get('error')}"
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "total_articles" in content
        assert "by_type" in content
        assert "total_links" in content
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_search():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_search",
            "arguments": {"query": "random graph"},
        }, msg_id=4)
        assert "result" in resp, f"Error: {resp.get('error')}"
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "results" in content
        assert content["total"] > 0
        # First result should be relevant
        titles = [r["title"].lower() for r in content["results"]]
        assert any("random" in t or "graph" in t for t in titles)
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_templates():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_templates",
            "arguments": {},
        }, msg_id=5)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "base" in content
        assert "process" in content
        assert "mission" in content
        assert "research-note" in content
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_list():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_list",
            "arguments": {},
        }, msg_id=6)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        articles = content["articles"]
        assert len(articles) > 0
        # Check structure of first article
        a = articles[0]
        assert "slug" in a
        assert "title" in a
        assert "type" in a
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_link():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_link",
            "arguments": {},
        }, msg_id=7)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "done"
        assert "total_links_created" in content
        assert "merge_candidates" in content
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_unknown_tool():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "nonexistent_tool",
            "arguments": {},
        }, msg_id=8)
        # Should get error in result content
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.asyncio
async def test_call_compare():
    proc = await _start_server()
    try:
        resp = await _mcp_request(proc, "tools/call", {
            "name": "ai_kos_compare",
            "arguments": {"slug": "random-graph-models"},
        }, msg_id=9)
        assert "result" in resp
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["slug"] == "random-graph-models"
        assert len(content["similar"]) > 0
    finally:
        proc.terminate()
        await proc.wait()
