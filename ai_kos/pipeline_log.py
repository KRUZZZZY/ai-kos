"""AI-KOS pipeline event log + projection cache.

Mirrors DeepSeek Harness' session persistence: the append-only event log
(``{id}.events.jsonl``) is the single **source of truth**; the ``{id}.json``
state file is a **write-behind projection** — a fold shortcut that is possibly
stale but never wrong. A ``ver`` mismatch discards the cache and replays from
the log rather than migrating stale data.

Invariants (ported from dsh):

- **append-only**: flushed events are never rewritten.
- **contiguous seq**: a parse failure in the *middle* of the log is committed
  corruption and raises :class:`EventLogCorruptError`; only a never-fully-
  written *final* line (a torn tail) is dropped.
- **durable-before-return**: :meth:`PipelineEventLog.append` flushes + fsyncs
  before returning.
- **crash-tail repair**: a step left ``running`` at the end of the log gets a
  synthetic ``interrupted`` closer on load (dsh's synthetic closers).

The fold (:func:`project_state`) is a pure function of the events — no side
effects, safe to call repeatedly.

stdlib only (json, os, pathlib, time, dataclasses, logging, copy).
"""

import copy
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai-kos.pipeline_log")


# ── Exceptions ──────────────────────────────────────────────────────────────

class EventLogError(Exception):
    """Base error for the pipeline event log."""


class EventLogCorruptError(EventLogError):
    """Committed mid-log corruption (parse failure / seq gap) — not a torn tail."""


# ── Events ──────────────────────────────────────────────────────────────────

@dataclass
class PipelineEvent:
    """One immutable, durable pipeline event."""

    seq: int
    type: str
    at: str
    payload: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {"seq": self.seq, "type": self.type, "at": self.at, "payload": self.payload},
            default=str,
        )

    @classmethod
    def from_line(cls, line: str) -> "PipelineEvent":
        data = json.loads(line)
        return cls(
            seq=int(data["seq"]),
            type=data["type"],
            at=data["at"],
            payload=data.get("payload", {}),
        )


# ── Event log ───────────────────────────────────────────────────────────────

class PipelineEventLog:
    """Append-only JSONL event log with contiguous seq + torn-tail repair.

    The log is opened in append mode; ``append`` assigns the next contiguous
    ``seq`` (last + 1) and fsyncs before returning.  A torn final line (crash
    mid-write) is dropped on open; committed mid-log corruption raises.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._last_seq = 0
        self.repair_tail()
        self._open()
        self._recompute_last_seq()

    # -- internals ----------------------------------------------------------

    def _open(self) -> None:
        self._file = open(self.path, "a", encoding="utf-8")

    def _read_events(self) -> List[PipelineEvent]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        events: List[PipelineEvent] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(PipelineEvent.from_line(line))
        return events

    def _recompute_last_seq(self) -> None:
        events = self._read_events()
        self._last_seq = events[-1].seq if events else 0

    # -- public API ---------------------------------------------------------

    def append(self, type: str, payload: dict) -> PipelineEvent:
        """Append one event; durable (flush + fsync) before returning.

        Raises :class:`EventLogError` when ``payload`` is not JSON-serializable.
        """
        try:
            json.dumps(payload)
        except (TypeError, ValueError) as exc:
            raise EventLogError(f"payload is not JSON-serializable: {exc}") from exc

        self._last_seq += 1
        event = PipelineEvent(
            seq=self._last_seq,
            type=type,
            at=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
        if self._file is None:
            self._open()
        self._file.write(event.to_json() + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
        return event

    def read(self) -> List[PipelineEvent]:
        """Return all events, in seq order."""
        return self._read_events()

    def read_from(self, seq: int) -> List[PipelineEvent]:
        """Return the suffix of events strictly after ``seq``."""
        return [e for e in self._read_events() if e.seq > seq]

    def tail(self) -> Optional[PipelineEvent]:
        """Return the last event, or ``None`` if the log is empty."""
        events = self._read_events()
        return events[-1] if events else None

    def repair_tail(self) -> None:
        """Drop a torn partial final line; raise on committed mid-log corruption."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        lines = self.path.read_text(encoding="utf-8").splitlines()
        kept: List[str] = []
        torn = False
        last_idx = len(lines) - 1
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                json.loads(line)
                kept.append(line)
            except ValueError:
                if i == last_idx:
                    torn = True  # torn tail — drop it
                else:
                    raise EventLogCorruptError(
                        f"corrupt event log at line {i + 1}: {self.path}"
                    ) from None
        if torn:
            tmp = self.path.with_name(self.path.name + ".repair.tmp")
            tmp.write_text(
                "\n".join(kept) + ("\n" if kept else ""), encoding="utf-8"
            )
            tmp.replace(self.path)

    def close(self) -> None:
        """Flush + close the append handle (idempotent)."""
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None


# ── Projection (fold) ───────────────────────────────────────────────────────

def project_state(events: List[PipelineEvent], base=None):
    """Fold events into a :class:`~ai_kos.pipeline.PipelineState`.

    Pure function — no side effects; ``base`` (if given) is never mutated.
    The first ``seeded`` event establishes identity (id/question/created_at and
    the initial step table); subsequent events update status, steps and context.
    """
    from ai_kos.pipeline import PipelineState, StepState

    state = copy.deepcopy(base) if base is not None else None

    for event in events:
        t = event.type
        p = event.payload or {}

        if t == "seeded":
            snapshot = p.get("state", p)
            state = PipelineState.from_json(json.dumps(snapshot, default=str))
            continue

        if state is None:
            raise EventLogError(
                f"cannot fold '{t}' event: no 'seeded' event and no base provided"
            )

        if t == "step_started":
            step = state.steps.setdefault(
                p["step"], StepState(name=p["step"], status="running")
            )
            step.status = "running"
            if p.get("started_at") is not None:
                step.started_at = p["started_at"]
            if p.get("attempts") is not None:
                step.attempts = p["attempts"]
        elif t == "step_completed":
            step = state.steps.setdefault(
                p["step"], StepState(name=p["step"], status="completed")
            )
            step.status = "completed"
            step.result = p.get("result")
            if p.get("completed_at") is not None:
                step.completed_at = p["completed_at"]
        elif t == "step_failed":
            step = state.steps.setdefault(
                p["step"], StepState(name=p["step"], status="failed")
            )
            step.status = "failed"
            step.last_error = p.get("last_error")
        elif t == "step_paused":
            step = state.steps.setdefault(
                p["step"], StepState(name=p["step"], status="paused")
            )
            step.status = "paused"
        elif t == "status_changed":
            state.status = p.get("status", state.status)
        elif t == "context_updated":
            state.context.update(p.get("context", {}))
        elif t == "interrupted":
            step = state.steps.setdefault(
                p["step"], StepState(name=p["step"], status="failed")
            )
            new_status = p.get("status", "failed")
            step.status = new_status
            step.last_error = p.get("last_error", "interrupted by crash")
            if new_status == "paused":
                state.status = "awaiting_review"
        # unknown event types are ignored (forward compatibility)

    if state is None:
        raise EventLogError("cannot project state: no 'seeded' event and no base provided")
    return state


# ── Projection cache ────────────────────────────────────────────────────────

class ProjectionCache:
    """Write-behind projection of the folded pipeline state.

    Writes are throttled except at mandatory points (``step_completed`` /
    ``step_failed`` / ``step_paused``), which flush immediately — mirroring
    dsh's turn/end checkpointing.  ``ver`` (the seq of the last applied event)
    is embedded in the JSON; a mismatch on :meth:`read` discards the cache and
    the caller replays the fold instead of migrating stale data.
    """

    def __init__(
        self,
        path,
        write_every_events: int = 5,
        write_interval_ms: int = 5000,
    ):
        self.path = Path(path)
        self.write_every_events = write_every_events
        self.write_interval_ms = write_interval_ms
        self._events_since_write = 0
        self._last_write_monotonic: Optional[float] = None
        self._pending_state: Any = None
        self._pending_seq: Optional[int] = None

    def write(self, state, seq: int, mandatory: bool = False) -> None:
        """Stage the state and flush immediately if mandatory, else throttle."""
        self._pending_state = state
        self._pending_seq = seq
        if mandatory:
            self._flush()
            return

        self._events_since_write += 1
        now = time.monotonic()
        elapsed_ms = (
            0.0
            if self._last_write_monotonic is None
            else (now - self._last_write_monotonic) * 1000.0
        )
        if (
            self._events_since_write >= self.write_every_events
            or elapsed_ms >= self.write_interval_ms
        ):
            self._flush()

    def _flush(self) -> None:
        if self._pending_state is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self._pending_state)
        data["ver"] = self._pending_seq
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        with open(tmp, "r+b") as f:
            os.fsync(f.fileno())
        tmp.replace(self.path)
        self._events_since_write = 0
        self._last_write_monotonic = time.monotonic()

    def read(self, events: List[PipelineEvent]):
        """Return the cached state iff ``ver`` == last event seq, else ``None``."""
        if not self.path.exists():
            return None
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (ValueError, OSError):
            return None  # corrupt projection → discard, replay from log

        last_seq = events[-1].seq if events else None
        if data.get("ver") != last_seq:
            return None  # stale → discard (never migrate)

        from ai_kos.pipeline import PipelineState

        return PipelineState.from_json(raw)
