#!/usr/bin/env python3
"""MCP server: VS Code Bridge — read/edit files in VS Code from Hermes.

Tools:
  vscode_detect_file  — auto-detect active file from recently modified .tex/.md
  vscode_set_file     — manually set the working file path
  vscode_status       — show current file + cursor position (from VS Code extension)
  vscode_read         — read the current file or a section of it
  vscode_edit         — replace text in the file (smart patch)
  vscode_cite         — search AI-KOS for relevant papers and generate \\cite{} insertion
  vscode_fix          — fix grammar, style, and sense-check the file (placeholder)

The VS Code extension (optional) writes ~/.hermes/vscode_state.json with:
  {"file": "/abs/path", "line": 42, "col": 10, "timestamp": "..."}

If the state file is missing or stale, falls back to detecting the most recently
modified .tex or .md file in the project directory.
"""

import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── State ────────────────────────────────────────────────────────────────────

STATE_FILE = Path.home() / '.hermes' / 'vscode_state.json'
WORKING_FILE = None  # Explicitly set file path
PROJECT_DIR = Path.home() / 'Documents' / 'AI_KOS_PROJECT'


def _find_active_file() -> dict:
    """Find the most likely active file: check VS Code state, then recently modified files."""
    # 1. Try VS Code extension state file
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            age = time.time() - os.path.getmtime(STATE_FILE)
            if age < 120 and state.get('file') and Path(state['file']).exists():
                return state
        except (json.JSONDecodeError, KeyError):
            pass

    # 2. Find most recently modified .tex or .md file in project
    candidates = []
    for ext in ['.tex', '.md', '.txt']:
        for f in PROJECT_DIR.rglob(f'*{ext}'):
            # Skip hidden dirs and knowledge/ bundles (those are KB articles)
            if any(p.startswith('.') for p in f.parts if p != '.'):
                continue
            if 'knowledge/bundles' in str(f):
                continue
            candidates.append((f, f.stat().st_mtime))

    candidates.sort(key=lambda x: x[1], reverse=True)

    if candidates:
        f, mtime = candidates[0]
        return {
            'file': str(f),
            'line': 1,
            'col': 1,
            'timestamp': datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            'source': 'recently_modified',
        }

    return {'file': None, 'error': 'No .tex or .md files found in project', 'source': 'none'}


def _read_file_safe(filepath: str) -> str:
    """Read a file, return empty string on error."""
    try:
        return Path(filepath).read_text()
    except Exception as e:
        return f""

def _write_file_safe(filepath: str, content: str) -> bool:
    """Write a file, return True on success."""
    try:
        Path(filepath).write_text(content)
        return True
    except Exception:
        return False


# ── Grammar / style check ───────────────────────────────────────────────────

# Fixes for common academic writing issues
GRAMMAR_FIXES = [
    # Oxford commas not enforced here — it's a style choice
    # Double spaces
    (r'  +', ' '),
    # Space before citation: "text \\cite{" → "text~\\cite{"
    (r'(\w) (\\cite\{)', r'\\1~\\2'),
    # Missing space after period: "end.A new" → "end. A new"
    (r'\.(\w)', r'. \1'),
    # LaTeX: fix unbalanced braces (basic check only — full brace matching needs a parser)
]

def _fix_grammar(text: str) -> tuple[str, list[str]]:
    """Apply grammar/style fixes. Returns (fixed_text, list_of_changes)."""
    changes = []
    fixed = text
    
    # 1. Fix double spaces
    double_spaces = len(re.findall(r'  +', fixed))
    if double_spaces:
        fixed = re.sub(r'  +', ' ', fixed)
        changes.append(f'Removed {double_spaces} double-space(s)')
    
    # 2. Fix space before citation
    cite_fixes = len(re.findall(r'(\w) (\\cite\{)', fixed))
    if cite_fixes:
        fixed = re.sub(r'(\w) (\\cite\{)', r'\1~\cite{', fixed)
        changes.append(f'Fixed {cite_fixes} space-before-citation (added ~)')
    
    # 3. Check for sentence spacing (period followed by capital letter without space)
    missing_space = len(re.findall(r'\.[A-Z]', fixed))
    if missing_space:
        # Only flag, don't auto-fix (could be abbreviations like "e.g.Foo")
        changes.append(f'Found {missing_space} possible missing spaces after periods (review manually)')
    
    # 4. Detect very long sentences (>60 words) — flag for review
    sentences = re.split(r'(?<=[.!?])\s+', fixed)
    long_sentences = [s for s in sentences if len(s.split()) > 60]
    if long_sentences:
        changes.append(f'Found {len(long_sentences)} very long sentence(s) (>60 words) — consider splitting')
    
    # 5. Passive voice indicators — flag
    passive_patterns = ['is shown', 'can be seen', 'was performed', 'were conducted',
                        'has been demonstrated', 'is considered', 'are presented']
    for pattern in passive_patterns:
        count = len(re.findall(pattern, fixed, re.IGNORECASE))
        if count:
            changes.append(f'Found {count}x "{pattern}" (passive voice — consider active)')
    
    if not changes:
        changes.append('No issues found')
    
    return fixed, changes


# ── Citation insertion ──────────────────────────────────────────────────────

def _find_citations_for_claim(claim: str, top_k: int = 3) -> list[dict]:
    """Search AI-KOS for papers relevant to a claim, return citation suggestions."""
    try:
        from ai_kos.search import search
        from ai_kos.bibtex import _parse_author_year_from_title
        
        results = search(claim, top_k=10, article_type='research-note')
        suggestions = []
        
        for r in results:
            title = r.get('title', '')
            author, year = _parse_author_year_from_title(title)
            if author and year:
                slug = r.get('slug', '')
                # Generate cite key
                cite_key = f"{author}{year}"
                # Check for disambiguation
                summary = r.get('summary', '')[:120]
                suggestions.append({
                    'cite_key': cite_key,
                    'slug': slug,
                    'title': title,
                    'author': author,
                    'year': year,
                    'summary': summary,
                    'score': r.get('score', 0),
                })
        
        return suggestions[:top_k]
    except Exception as e:
        return [{'error': str(e)}]


# ── Server entrypoint ───────────────────────────────────────────────────────

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

server = Server("vscode-bridge")


async def handle_list_tools_vsc(_ctx, _req: types.ListToolsRequest) -> types.ListToolsResult:
    tools = [
        types.Tool(
            name="vscode_detect_file",
            description="Auto-detect the currently active file in VS Code. Checks the VS Code extension state file first, then falls back to the most recently modified .tex/.md file in the project.",
            input_schema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="vscode_set_file",
            description="Set the file path that Hermes should work on. Use this once at the start of your session.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute path to the file you're editing"}},
                "required": ["path"]
            }
        ),
        types.Tool(
            name="vscode_status",
            description="Show which file is currently active (set via vscode_set_file or auto-detected), plus line count and last-modified time.",
            input_schema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="vscode_read",
            description="Read the current file (or a section of it). Use offset/limit for large files.",
            input_schema={
                "type": "object",
                "properties": {
                    "offset": {"type": "integer", "description": "Line to start from (1-indexed)", "default": 1},
                    "limit": {"type": "integer", "description": "Max lines to return", "default": 500},
                }
            }
        ),
        types.Tool(
            name="vscode_edit",
            description="Replace text in the current file. The file is saved immediately and VS Code auto-reloads it.",
            input_schema={
                "type": "object",
                "properties": {
                    "old_string": {"type": "string", "description": "Exact text to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                    "replace_all": {"type": "boolean", "description": "Replace all occurrences", "default": False},
                },
                "required": ["old_string", "new_string"]
            }
        ),
        types.Tool(
            name="vscode_cite",
            description="Search AI-KOS knowledge base for papers relevant to a claim and suggest BibTeX \\cite{} keys.",
            input_schema={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The sentence or paragraph you want citations for"},
                    "top_k": {"type": "integer", "description": "Max citations to return", "default": 3},
                },
                "required": ["claim"]
            }
        ),
        types.Tool(
            name="vscode_fix",
            description="Fix grammar, style, and LaTeX formatting issues in the current file. Checks: double spaces, citation spacing, long sentences, passive voice.",
            input_schema={
                "type": "object",
                "properties": {
                    "auto_fix": {"type": "boolean", "description": "Auto-apply safe fixes (double spaces, citation spacing)", "default": False},
                }
            }
        ),
    ]
    return types.ListToolsResult(tools=tools)


async def handle_call_tool_vsc(_ctx, req: types.CallToolRequestParams) -> types.CallToolResult:
    global WORKING_FILE
    name = req.name
    args = req.arguments or {}
    
    try:
        if name == 'vscode_detect_file':
            state = _find_active_file()
            if state.get('file'):
                WORKING_FILE = state['file']
            result = state
        
        elif name == 'vscode_set_file':
            path = args['path']
            if not Path(path).exists():
                result = {"error": f"File not found: {path}"}
            else:
                WORKING_FILE = path
                result = {
                    "status": "set", "file": path,
                    "size": Path(path).stat().st_size,
                    "lines": len(Path(path).read_text().splitlines())
                }
        
        elif name == 'vscode_status':
            current = WORKING_FILE
            if not current:
                state = _find_active_file()
                current = state.get('file')
            
            if not current or not Path(current).exists():
                result = {
                    "file": current, "status": "not found or not set",
                    "hint": "Use vscode_set_file to specify your file, or vscode_detect_file to auto-detect"
                }
            else:
                p = Path(current)
                content = p.read_text()
                result = {
                    "file": str(p),
                    "size": p.stat().st_size,
                    "lines": len(content.splitlines()),
                    "modified": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "chars": len(content),
                    "words": len(content.split()),
                }
        
        elif name == 'vscode_read':
            current = WORKING_FILE or (_find_active_file().get('file'))
            if not current:
                result = {"error": "No file set. Use vscode_set_file or vscode_detect_file first."}
            else:
                offset = args.get('offset', 1)
                limit = args.get('limit', 500)
                lines = Path(current).read_text().splitlines()
                total = len(lines)
                start = max(0, offset - 1)
                end = start + limit
                selected = lines[start:end]
                result = {
                    "file": current,
                    "total_lines": total,
                    "offset": offset,
                    "content": '\n'.join(selected),
                    "truncated": end < total,
                }
        
        elif name == 'vscode_edit':
            current = WORKING_FILE or (_find_active_file().get('file'))
            if not current:
                result = {"error": "No file set. Use vscode_set_file or vscode_detect_file first."}
            else:
                old = args['old_string']
                new = args['new_string']
                replace_all = args.get('replace_all', False)
                content = Path(current).read_text()
                
                if replace_all:
                    count = content.count(old)
                    if count == 0:
                        result = {"error": "old_string not found in file"}
                    else:
                        content = content.replace(old, new)
                        Path(current).write_text(content)
                        result = {"status": "edited", "file": current, "replacements": count}
                else:
                    if content.count(old) == 0:
                        result = {"error": "old_string not found in file"}
                    elif content.count(old) > 1:
                        result = {
                            "error": f"old_string appears {content.count(old)} times. Use replace_all=true or provide more context to make it unique."
                        }
                    else:
                        content = content.replace(old, new, 1)
                        Path(current).write_text(content)
                        result = {"status": "edited", "file": current, "replacements": 1}
        
        elif name == 'vscode_cite':
            claim = args['claim']
            top_k = args.get('top_k', 3)
            suggestions = _find_citations_for_claim(claim, top_k)
            cite_keys = [s['cite_key'] for s in suggestions if 'cite_key' in s]
            cite_cmd = f"\\cite{{{','.join(cite_keys)}}}" if cite_keys else None
            result = {
                "claim": claim[:200],
                "suggestions": suggestions,
                "cite_command": cite_cmd,
                "hint": "Use vscode_edit to insert the citation into your file at the desired location."
            }
        
        elif name == 'vscode_fix':
            current = WORKING_FILE or (_find_active_file().get('file'))
            if not current:
                result = {"error": "No file set. Use vscode_set_file or vscode_detect_file first."}
            else:
                auto_fix = args.get('auto_fix', False)
                content = Path(current).read_text()
                fixed, changes = _fix_grammar(content)
                if auto_fix and fixed != content:
                    Path(current).write_text(fixed)
                    result = {"status": "fixed", "file": current, "changes": changes}
                else:
                    result = {
                        "status": "analyzed" if not auto_fix else "no_changes",
                        "file": current,
                        "changes": changes,
                        "hint": "Set auto_fix=true to automatically apply safe fixes." if not auto_fix else None,
                    }
        
        else:
            result = {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        import traceback
        result = {"error": str(e), "traceback": traceback.format_exc()}
    
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result, indent=2, default=str, ensure_ascii=False))]
    )


# ── Server entrypoint ───────────────────────────────────────────────────────

# Server and handlers already defined above

server.add_request_handler("tools/list", types.ListToolsRequest, handle_list_tools_vsc)
server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool_vsc)


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def entrypoint():
    asyncio.run(main())


if __name__ == "__main__":
    entrypoint()
