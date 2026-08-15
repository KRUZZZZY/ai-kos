"""AI-KOS audit log — the "model-visible ⟺ logged" invariant.

INVARIANT: anything that reaches a model request must be reconstructable from
this log (DeepSeek Harness invariant: "model-visible ⟺ logged"). Every write
that feeds model context is recorded as an append-only JSONL entry with a
contiguous ``seq``, durable-before-return (fsync), and preview-capped content.

A torn final line (crash artifact) is dropped on repair; corruption in the
MIDDLE of the log raises :class:`AuditError` (committed corruption ≠ torn
tail).

Integration points:
- ``atq_worker`` logs the rendered objective/command handed to workers/lanes
  (source ``atq-worker``, meta carries ``task_id`` + ``lane``).
- TODO(pipeline): log question / sub_questions / findings at step boundaries
  (source ``pipeline:<id>``, meta ``{step}``) — deferred to avoid touching
  pipeline.py here (owned by another subagent); the log is ready to accept it.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ai_kos.config import get

logger = logging.getLogger("ai-kos.audit")


class AuditError(Exception):
    """Base error for audit log failures (committed corruption)."""


@dataclass
class AuditEntry:
    seq: int
    at: str
    source: str
    kind: str
    preview: str
    meta: dict


def default_audit_path() -> Path:
    """Default audit log path: ``<knowledge_dir>/audit/audit.jsonl``."""
    knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
    return Path(knowledge_dir) / "audit" / "audit.jsonl"


class AuditLog:
    """Append-only, seq-numbered, durable audit trail."""

    def __init__(self, path: Optional[Any] = None):
        self.path = Path(path) if path else default_audit_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._next_seq = self._scan_next_seq()

    # ── internals ─────────────────────────────────────────────────────────

    def repair_tail(self) -> None:
        """Drop a torn partial final line; raise on committed mid-log corruption."""
        if not self.path.exists():
            return
        data = self.path.read_text()
        if not data.strip():
            return
        lines = data.splitlines()
        bad_index = None
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                bad_index = i
                break
        if bad_index is None:
            return
        last_nonempty = max((i for i, l in enumerate(lines) if l.strip()), default=-1)
        if bad_index < last_nonempty:
            raise AuditError(f"corrupt audit log at line {bad_index + 1}: {self.path}")
        good = [l for l in lines[:bad_index] if l.strip()]
        self.path.write_text("\n".join(good) + ("\n" if good else ""))
        logger.warning("audit: dropped torn tail line in %s", self.path)

    def _lines(self) -> list:
        if not self.path.exists():
            return []
        return self.path.read_text().splitlines()

    def _scan_next_seq(self) -> int:
        self.repair_tail()
        last = None
        for line in self._lines():
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                continue
        return (int(last["seq"]) + 1) if last else 1

    def _iter_entries(self):
        self.repair_tail()
        for i, line in enumerate(self._lines()):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                raise AuditError(f"corrupt audit log at line {i + 1}: {self.path}")
            yield data

    # ── API ───────────────────────────────────────────────────────────────

    def log(self, source: str, content: str, kind: str = "model_input",
            meta: Optional[dict] = None, preview_chars: int = 500) -> AuditEntry:
        """Append one entry. Durable before returning (flush + fsync)."""
        self.repair_tail()  # keep the tail clean before appending
        entry = AuditEntry(
            seq=self._next_seq,
            at=datetime.now(timezone.utc).isoformat(),
            source=source,
            kind=kind,
            preview=content[:preview_chars],
            meta=meta or {},
        )
        self._next_seq += 1
        try:
            line = json.dumps(asdict(entry))
        except TypeError as e:
            raise AuditError(f"meta not JSON-serializable: {e}") from e
        with open(self.path, "a") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry

    def read(self, source: Optional[str] = None, kind: Optional[str] = None,
             since_seq: Optional[int] = None) -> list[AuditEntry]:
        """Read entries, optionally filtered by source / kind / seq floor."""
        out = []
        for data in self._iter_entries():
            if since_seq is not None and int(data["seq"]) <= since_seq:
                continue
            if source is not None and data.get("source") != source:
                continue
            if kind is not None and data.get("kind") != kind:
                continue
            out.append(AuditEntry(**data))
        return out

    def tail(self) -> Optional[AuditEntry]:
        entries = self.read()
        return entries[-1] if entries else None


def log_model_visible(source: str, content: str, kind: str = "model_input",
                      meta: Optional[dict] = None, preview_chars: int = 500) -> AuditEntry:
    """Convenience: log a model-visible input against the default audit log."""
    return AuditLog().log(source, content, kind=kind, meta=meta, preview_chars=preview_chars)
