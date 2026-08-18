"""ATQ Director — MCP server that lets a queue-manager agent DIRECT worker agents.

Gives an ATQ agent (e.g. the atq-manager profile) real hands: list board state,
spawn workers (create + dispatch kanban cards), dispatch ready cards, comment,
and run one ai-kos tick. Wraps the `hermes kanban` and `ai-kos atq` CLIs so it
always operates on the same SQLite substrate the dispatcher uses — claims,
leases, and no-clobber guarantees come from kanban itself.

All tools are T0/T1 (read-only or reversible) per the ATQ least-risk protocol:
creating/dispatching cards is reversible (cards can be blocked or deleted);
nothing here can destroy data. Destructive decisions stay with humans.

Usage:
    python3 -m ai_kos.atq_director            # stdio MCP server
    python3 -m ai_kos.atq_director --smoke    # run tool fns directly, no MCP

Registered in ~/.hermes/config.yaml under mcp_servers.atq-director; add
"atq-director" to a profile's toolsets to expose these tools to that agent.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from ai_kos.atq import record_spawn, spawn_gate

server = Server("atq-director")

TASK_ID_RE = re.compile(r"\b(t_[a-z0-9]+)\b")

_BOARD_DESC = "Kanban board slug (e.g. 'mission-atq-agent-task-queue-mission')."

TOOLS = [
    types.Tool(
        name="atq_status",
        description="Read-only board snapshot: tasks with status + assignee, plus counts. Use this first to see what needs doing.",
        input_schema={"type": "object", "properties": {"board": {"type": "string", "description": _BOARD_DESC, "default": "default"}}},
    ),
    types.Tool(
        name="atq_show",
        description="Read-only full task detail: body, status, assignee, parents/children, events.",
        input_schema={"type": "object", "properties": {
            "task_id": {"type": "string", "description": "Kanban task id (t_xxxx)"},
            "board": {"type": "string", "description": _BOARD_DESC, "default": "default"},
        }, "required": ["task_id"]},
    ),
    types.Tool(
        name="atq_workers",
        description="Read-only list of currently running worker cards on a board.",
        input_schema={"type": "object", "properties": {"board": {"type": "string", "description": _BOARD_DESC, "default": "default"}}},
    ),
    types.Tool(
        name="atq_spawn_worker",
        description="DIRECT an agent: create a worker card assigned to a profile and dispatch it. The spawned worker gets lease + heartbeat + no-clobber guarantees. Reversible: the card can be blocked or deleted.",
        input_schema={"type": "object", "properties": {
            "board": {"type": "string", "description": _BOARD_DESC},
            "title": {"type": "string", "description": "Card title"},
            "body": {"type": "string", "description": "Full task body — include acceptance criteria for the tester"},
            "assignee": {"type": "string", "description": "Hermes profile name to run the task (e.g. 'delegtest', 'atq-tester')"},
            "parent": {"type": "string", "description": "Optional parent task id to link under"},
            "priority": {"type": "integer", "description": "Lower = higher priority (default 0)"},
        }, "required": ["board", "title", "body", "assignee"]},
    ),
    types.Tool(
        name="atq_dispatch",
        description="Dispatch ready cards on a board: spawn worker processes for ready tasks.",
        input_schema={"type": "object", "properties": {
            "board": {"type": "string", "description": _BOARD_DESC, "default": "default"},
            "max_n": {"type": "integer", "description": "Cap on spawns this pass (default 2)"},
            "dry_run": {"type": "boolean", "description": "Preview without spawning (default false)"},
        }},
    ),
    types.Tool(
        name="atq_comment",
        description="Post a comment on a task card — used for reports, escalation, coordination.",
        input_schema={"type": "object", "properties": {
            "task_id": {"type": "string", "description": "Kanban task id"},
            "body": {"type": "string", "description": "Comment text"},
            "board": {"type": "string", "description": _BOARD_DESC, "default": "default"},
            "author": {"type": "string", "description": "Author label (default 'atq-director')"},
        }, "required": ["task_id", "body"]},
    ),
    types.Tool(
        name="atq_tick",
        description="Run one ai-kos ATQ tick on a board: decompose triage roots, collect blocked, enforce spawn caps, dispatch. Equivalent to the cron wrapper.",
        input_schema={"type": "object", "properties": {"board": {"type": "string", "description": _BOARD_DESC, "default": "default"}}},
    ),
]
# hermes binary resolution: HERMES_BIN env > PATH > known venv location
_KNOWN_HERMES = Path.home() / ".hermes/hermes-agent/venv/bin/hermes"
_KNOWN_AIKOS = Path.home() / ".local/bin/ai-kos"


def _hermes_bin() -> str:
    env = os.environ.get("HERMES_BIN")
    if env and Path(env).exists():
        return env
    found = shutil.which("hermes")
    if found:
        return found
    if _KNOWN_HERMES.exists():
        return str(_KNOWN_HERMES)
    raise RuntimeError("hermes binary not found (set HERMES_BIN)")


def _ai_kos_bin() -> str:
    """Resolve the ai-kos CLI (used by atq_tick): AI_KOS_BIN > PATH > known path."""
    env = os.environ.get("AI_KOS_BIN")
    if env and Path(env).exists():
        return env
    found = shutil.which("ai-kos")
    if found:
        return found
    if _KNOWN_AIKOS.exists():
        return str(_KNOWN_AIKOS)
    raise RuntimeError("ai-kos binary not found (set AI_KOS_BIN)")


def _run(cmd: list[str], timeout: int = 120) -> dict:
    """Run a command, return {exit_code, stdout, stderr}."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": f"timed out after {timeout}s"}
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def _kanban(board: str, sub: str, *args: str, timeout: int = 120) -> dict:
    """hermes kanban --board <slug> <sub> [args...] — board is a TOP-LEVEL flag."""
    return _run([_hermes_bin(), "kanban", "--board", board, sub, *args], timeout=timeout)


def _task_id_from(text: str) -> str | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
    except (json.JSONDecodeError, AttributeError):
        pass
    m = TASK_ID_RE.search(text)
    return m.group(1) if m else None


def _fmt(r: dict) -> str:
    """Compact single-string render of a command result for LLM consumption."""
    out = r["stdout"]
    if r["exit_code"] != 0:
        out = f"exit={r['exit_code']}\n{out}\n{r['stderr']}"
    return out.strip() or "(no output)"


# ── tools ───────────────────────────────────────────────────────────────────

def atq_status(board: str = "default") -> str:
    r = _kanban(board, "list", "--json")
    lines = [f"board: {board}"]
    try:
        tasks = json.loads(r["stdout"])
        if isinstance(tasks, list):
            by_status: dict[str, int] = {}
            for t in tasks:
                st = t.get("status", "?")
                by_status[st] = by_status.get(st, 0) + 1
                lines.append(f"- {t.get('id')} [{st}] assignee={t.get('assignee')} {t.get('title')}")
            lines.insert(1, f"counts: {json.dumps(by_status)}")
            return "\n".join(lines)
    except json.JSONDecodeError:
        pass
    return _fmt(r)


def atq_show(task_id: str, board: str = "default") -> str:
    return _fmt(_kanban(board, "show", task_id))


def atq_workers(board: str = "default") -> str:
    r = _kanban(board, "list", "--json")
    try:
        tasks = json.loads(r["stdout"])
        if isinstance(tasks, list):
            running = [t for t in tasks if t.get("status") == "running"]
            if not running:
                return f"board {board}: no running workers"
            return "\n".join(
                f"- {t.get('id')} assignee={t.get('assignee')} started={t.get('started_at')} {t.get('title')}"
                for t in running
            )
    except json.JSONDecodeError:
        pass
    return _fmt(r)


def atq_spawn_worker(board: str, title: str, body: str, assignee: str,
                     parent: str | None = None, priority: int = 0) -> str:
    # Spawn gate (audit finding #5): the paused kill-switch and the daily cap
    # apply to direct spawns too, not just the tick loop.
    allowed, reason = spawn_gate(board)
    if not allowed:
        return f"spawn refused: {reason}"
    args = ["--body", body, "--assignee", assignee, "--priority", str(priority)]
    if parent:
        args += ["--parent", parent]
    r = _kanban(board, "create", "--json", *args, title, timeout=180)
    if r["exit_code"] != 0:
        return f"create failed: {_fmt(r)}"
    task_id = _task_id_from(r["stdout"])
    if not task_id:
        return f"could not parse task id from: {_fmt(r)}"
    # NOTE: dispatch --max is a LIVE CONCURRENCY CAP (running tasks + spawns),
    # not a per-tick budget — a board with 1 running task needs --max >= 2.
    disp = _kanban(board, "dispatch", "--max", "2", "--json", timeout=180)
    if disp["exit_code"] == 0:
        record_spawn(board)
    return f"created {task_id} (assignee={assignee})\ndispatch: {_fmt(disp)}"


def atq_dispatch(board: str = "default", max_n: int = 2, dry_run: bool = False) -> str:
    if dry_run:
        return _fmt(_kanban(board, "dispatch", "--json", "--max", str(max_n),
                            "--dry-run", timeout=300))
    allowed, reason = spawn_gate(board)
    if not allowed:
        return f"dispatch refused: {reason}"
    r = _kanban(board, "dispatch", "--json", "--max", str(max_n), timeout=300)
    if r["exit_code"] == 0:
        m = re.search(r"(?i)spawned[:\s]+(\d+)", r["stdout"])
        record_spawn(board, n=int(m.group(1)) if m else max_n)
    return _fmt(r)


def atq_comment(task_id: str, body: str, board: str = "default", author: str = "atq-director") -> str:
    return _fmt(_kanban(board, "comment", "--author", author, task_id, body))


def atq_tick(board: str = "default") -> str:
    return _fmt(_run([_ai_kos_bin(), "atq", "tick", "--board", board], timeout=300))


def _dispatch_tool(name: str, arguments: dict):
    if name == "atq_status":
        return {"result": atq_status(arguments.get("board", "default"))}
    if name == "atq_show":
        return {"result": atq_show(arguments["task_id"], arguments.get("board", "default"))}
    if name == "atq_workers":
        return {"result": atq_workers(arguments.get("board", "default"))}
    if name == "atq_spawn_worker":
        return {"result": atq_spawn_worker(
            arguments["board"], arguments["title"], arguments["body"], arguments["assignee"],
            arguments.get("parent"), arguments.get("priority", 0))}
    if name == "atq_dispatch":
        return {"result": atq_dispatch(arguments.get("board", "default"),
                                       arguments.get("max_n", 2), arguments.get("dry_run", False))}
    if name == "atq_comment":
        return {"result": atq_comment(arguments["task_id"], arguments["body"],
                                      arguments.get("board", "default"), arguments.get("author", "atq-director"))}
    if name == "atq_tick":
        return {"result": atq_tick(arguments.get("board", "default"))}
    return {"error": f"Unknown tool: {name}"}


# ── MCP handlers ────────────────────────────────────────────────────────────

async def handle_list_tools(_ctx, _req: types.ListToolsRequest) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(_ctx, req: types.CallToolRequestParams) -> types.CallToolResult:
    try:
        result = await asyncio.to_thread(_dispatch_tool, req.name, req.arguments or {})
    except Exception as exc:
        result = {"error": str(exc), "tool": req.name}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    )


server.add_request_handler("tools/list", types.ListToolsRequest, handle_list_tools)
server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def entrypoint():
    asyncio.run(main())


def _smoke() -> None:
    print("== atq_status(default) ==")
    print(atq_status("default"))
    print("\n== atq_workers(mission board) ==")
    print(atq_workers("mission-atq-agent-task-queue-mission"))


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        _smoke()
    else:
        entrypoint()
