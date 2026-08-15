"""AI-KOS ATQ worker lanes — named providers for external agent CLIs.

Mirrors DeepSeek Harness' subagent capability: one registry, named providers
that decide where a child runs. Here the providers are deterministic wrappers
around external coding-agent CLIs (codex / claude / opencode) plus a plain
shell lane. NO LLM calls in this module — it is a spawn/enumerate layer.

Status vocabulary (dsh list_agents): ``running`` (active run), ``idle``
(resident, between turns), ``ready`` (resumable-but-inactive — a completed
lane run leaves a persisted artifact, so the work is resumable, not terminal).

Lane result artifacts follow the ATQ no-clobber convention:
``<task_id>-lane-<lane>.out`` in the claim workspace (``spec.workdir``).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ai-kos.atq-lanes")

STDOUT_PREVIEW_CHARS = 2000


class LaneError(Exception):
    """Base error for lane operations."""


@dataclass
class LaneSpec:
    """How to spawn one lane run: CLI + args + env + timeout + workspace."""

    name: str
    cmd: List[str]
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    timeout: int = 600
    task_id: str = ""
    workdir: Optional[Path] = None


@dataclass
class LaneStatus:
    """Enumeration view of one lane (dsh running/idle/ready vocabulary)."""

    name: str
    status: str  # running | idle | ready
    detail: str = ""


@dataclass
class LaneResult:
    """Outcome of one lane spawn: bounded preview + artifact path."""

    lane: str
    exit_code: int
    stdout_preview: str
    artifact: Optional[str]
    ran_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LaneProvider:
    """Provider contract: spawn a run; report current status."""

    name = "base"

    def spawn(self, spec: LaneSpec) -> LaneResult:
        raise NotImplementedError

    def status(self) -> LaneStatus:
        return LaneStatus(name=self.name, status="ready")


class ShellLane(LaneProvider):
    """Runs a shell command as the lane (the default local worker)."""

    name = "shell"

    def spawn(self, spec: LaneSpec) -> LaneResult:
        cmd = spec.cmd + (spec.args or [])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=spec.timeout, env=spec.env)
            exit_code, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return LaneResult(lane=self.name, exit_code=124,
                              stdout_preview="timed out",
                              artifact=None, ran_at=_now())
        except FileNotFoundError:
            return LaneResult(lane=self.name, exit_code=127,
                              stdout_preview=f"lane CLI not found: {cmd[0]}",
                              artifact=None, ran_at=_now())
        preview = (out or err).strip()[:STDOUT_PREVIEW_CHARS]
        artifact = None
        if spec.task_id:
            workdir = spec.workdir or Path.cwd()
            p = workdir / f"{spec.task_id}-lane-{self.name}.out"
            p.write_text((out or "") + ("\n--- stderr ---\n" + (err or "") if err else ""))
            artifact = str(p)
        return LaneResult(lane=self.name, exit_code=exit_code,
                          stdout_preview=preview, artifact=artifact, ran_at=_now())


class CodexLane(LaneProvider):
    """External Codex CLI lane (codex exec ...)."""

    name = "codex"

    def spawn(self, spec: LaneSpec) -> LaneResult:
        return ShellLane().spawn(LaneSpec(
            name=self.name, cmd=[shutil.which("codex") or "codex", "exec"],
            args=spec.args or spec.cmd, env=spec.env, timeout=spec.timeout,
            task_id=spec.task_id, workdir=spec.workdir))


class ClaudeCodeLane(LaneProvider):
    """External Claude Code CLI lane (claude -p ...)."""

    name = "claude"

    def spawn(self, spec: LaneSpec) -> LaneResult:
        return ShellLane().spawn(LaneSpec(
            name=self.name, cmd=[shutil.which("claude") or "claude", "-p"],
            args=spec.args or spec.cmd, env=spec.env, timeout=spec.timeout,
            task_id=spec.task_id, workdir=spec.workdir))


class OpenCodeLane(LaneProvider):
    """External OpenCode CLI lane (opencode run ...)."""

    name = "opencode"

    def spawn(self, spec: LaneSpec) -> LaneResult:
        return ShellLane().spawn(LaneSpec(
            name=self.name, cmd=[shutil.which("opencode") or "opencode", "run"],
            args=spec.args or spec.cmd, env=spec.env, timeout=spec.timeout,
            task_id=spec.task_id, workdir=spec.workdir))


class LaneRegistry:
    """Named lane providers; duplicate/unknown names fail loud (dsh contract)."""

    def __init__(self):
        self._providers: Dict[str, LaneProvider] = {}

    def register(self, provider: LaneProvider) -> None:
        if provider.name in self._providers:
            raise LaneError(f"lane already registered: {provider.name}")
        self._providers[provider.name] = provider

    def get(self, name: str) -> LaneProvider:
        """Look up a lane; unknown names raise (never silently None)."""
        provider = self._providers.get(name)
        if provider is None:
            raise LaneError(f"unknown lane: {name}")
        return provider

    def list(self) -> List[str]:
        return list(self._providers.keys())

    def spawn(self, name: str, spec: LaneSpec) -> LaneResult:
        return self.get(name).spawn(spec)

    def status_all(self) -> List[LaneStatus]:
        return [p.status() for p in self._providers.values()]


def lane_status_all(registry: LaneRegistry) -> List[LaneStatus]:
    """dsh list_agents-style enumeration of every registered lane."""
    return registry.status_all()


def register_default_lanes(registry: LaneRegistry) -> None:
    """Register the shell lane always; external CLIs only when installed."""
    registry.register(ShellLane())
    for lane_cls in (CodexLane, ClaudeCodeLane, OpenCodeLane):
        exe = lane_cls().name
        if shutil.which(exe):
            registry.register(lane_cls())
            logger.info("registered external lane: %s", exe)
        else:
            logger.debug("external lane %s skipped (CLI not found)", exe)


def default_registry() -> LaneRegistry:
    reg = LaneRegistry()
    register_default_lanes(reg)
    return reg
