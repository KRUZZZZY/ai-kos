"""AI-KOS ResearchPipeline — durable execution engine for deep research.

Adopts Cloudflare Workflows' step-based durable execution pattern:
- Each step is wrapped with retry + exponential backoff
- Pipeline state persisted to JSON after each step
- Pause/resume across Hermes sessions
- Human review gate before article creation

Persistence model (dsh session-persistence port):
- ``{id}.events.jsonl`` is the append-only *source of truth*.
- ``{id}.json`` is a *write-behind projection* (``ver`` = seq of last applied
  event); a ``ver`` mismatch on load discards it and replays the log.

Built with zero external dependencies (json + pathlib + stdlib).
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from ai_kos.config import get
from ai_kos.pipeline_log import PipelineEventLog, ProjectionCache, project_state

logger = logging.getLogger("ai-kos.pipeline")

PIPELINE_DIR_NAME = "pipelines"
MAX_RETRIES = 3
BASE_DELAY = 2  # seconds, doubles each retry

# Event types whose projection write is mandatory (flushed immediately).
_MANDATORY_EVENT_TYPES = ("step_completed", "step_failed", "step_paused")


# ── Exceptions ──────────────────────────────────────────────────────────────

class PipelineError(Exception):
    """Base exception for pipeline failures."""

class StepFailedError(PipelineError):
    """A step failed after exhausting retries."""

class PipelinePausedError(PipelineError):
    """Pipeline is paused awaiting human review."""


# ── State Model ─────────────────────────────────────────────────────────────

@dataclass
class StepState:
    """Recorded state of a single pipeline step."""
    name: str
    status: str           # pending | running | completed | failed | paused
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    result: Any = None    # step output (serializable)


@dataclass
class PipelineState:
    """Full durable state of a research pipeline run."""
    id: str
    question: str
    status: str = "planned"           # planned | running | awaiting_review | completed | failed
    steps: Dict[str, StepState] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    @classmethod
    def from_json(cls, data: str) -> "PipelineState":
        raw = json.loads(data)
        raw.pop("ver", None)  # projection cache marker — not part of the state
        steps = {}
        for name, s in raw.get("steps", {}).items():
            steps[name] = StepState(**s)
        raw["steps"] = steps
        return cls(**raw)


def _default_pipelines_dir() -> Path:
    knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
    return Path(knowledge_dir) / PIPELINE_DIR_NAME


# ── Event-log helpers (source-of-truth fold) ───────────────────────────────

def _snapshot_dict(state: PipelineState) -> dict:
    """A JSON-friendly snapshot of ``state``, minus the volatile ``updated_at``."""
    d = asdict(state)
    d.pop("updated_at", None)
    return d


def _diff_events(prev: Optional[dict], curr: dict) -> List[tuple]:
    """Derive the event(s) that transform snapshot ``prev`` into ``curr``.

    Returns a list of ``(event_type, payload)`` tuples in fold order.  A step
    status transition emits the matching step event; overall status and context
    changes emit ``status_changed`` / ``context_updated`` respectively.
    """
    events: List[tuple] = []
    if prev is None:
        return events

    if prev.get("status") != curr.get("status"):
        events.append(("status_changed", {"status": curr.get("status")}))

    prev_steps = prev.get("steps", {})
    curr_steps = curr.get("steps", {})
    for name, st in curr_steps.items():
        pst = prev_steps.get(name)
        if pst is None:
            continue
        if pst.get("status") == st.get("status"):
            continue
        new_status = st.get("status")
        if new_status == "running":
            events.append(("step_started", {
                "step": name,
                "started_at": st.get("started_at"),
                "attempts": st.get("attempts"),
            }))
        elif new_status == "completed":
            events.append(("step_completed", {
                "step": name,
                "result": st.get("result"),
                "completed_at": st.get("completed_at"),
            }))
        elif new_status == "failed":
            events.append(("step_failed", {
                "step": name,
                "last_error": st.get("last_error"),
            }))
        elif new_status == "paused":
            events.append(("step_paused", {"step": name}))

    if prev.get("context") != curr.get("context"):
        events.append(("context_updated", {"context": curr.get("context", {})}))

    return events


def _repair_crash_tail(log: PipelineEventLog, events: List[Any]) -> None:
    """Append a synthetic ``interrupted`` closer for a step left running.

    dsh's crash-tail repair: if the most recent ``step_started`` has no matching
    terminal (``step_completed``/``step_failed``/``step_paused``) after it, the
    pipeline crashed mid-step — close it (step → failed) rather than truncate.
    """
    if not events:
        return
    last_started_idx = -1
    last_started = None
    for i, e in enumerate(events):
        if e.type == "step_started":
            last_started = e
            last_started_idx = i
    if last_started is None:
        return
    step_name = last_started.payload.get("step")
    terminal_after = any(
        e.type in ("step_completed", "step_failed", "step_paused")
        and e.payload.get("step") == step_name
        for e in events[last_started_idx + 1:]
    )
    if not terminal_after:
        log.append("interrupted", {
            "step": step_name,
            "status": "failed",
            "last_error": "interrupted by crash",
        })


# ── Pipeline Engine ─────────────────────────────────────────────────────────

class ResearchPipeline:
    """Durable research pipeline with retry, state persistence, and pause/resume.

    Steps (in order):
      1. plan          — decompose question into sub-questions
      2. search        — web search each sub-question
      3. structure     — structure raw results into typed findings
      4. cross_ref     — cross-reference against AI-KOS knowledge base
      5. synthesize    — generate synthesis report
      6. review        — pause for human review
      7. persist       — create AI-KOS articles

    Usage:
        pipeline = ResearchPipeline("What is climate change?")
        pipeline.run(search_fn=my_search_function)

    Resume:
        pipeline = ResearchPipeline.load("pipelines/abc123.json")
        pipeline.resume(search_fn=my_search_function)
    """

    # Ordered list of step names
    STEPS = [
        "plan",
        "search",
        "structure",
        "cross_ref",
        "synthesize",
        "review",
        "persist",
    ]

    def __init__(self, state: PipelineState, pipelines_dir: Optional[str] = None):
        self.state = state
        self._dir = Path(pipelines_dir) if pipelines_dir else self._default_dir()
        # Event log (append-only source of truth) + write-behind projection.
        # Both materialize lazily on the first save.
        self._log: Optional[PipelineEventLog] = None
        self._projection: Optional[ProjectionCache] = None
        self._last_snapshot: Optional[dict] = None

    @classmethod
    def create(cls, question: str, pipelines_dir: Optional[str] = None) -> "ResearchPipeline":
        """Create a new pipeline for a research question."""
        pid = str(uuid.uuid4())[:8]
        state = PipelineState(
            id=pid,
            question=question,
            steps={name: StepState(name=name, status="pending") for name in cls.STEPS},
        )
        return cls(state, pipelines_dir=pipelines_dir)

    @classmethod
    def load(cls, filepath: str) -> "ResearchPipeline":
        """Resume a pipeline from its JSON state file (+ event log if present).

        The ``{id}.json`` file is a write-behind projection: when the event log
        exists, a matching ``ver`` is a fast path; otherwise the state is
        replayed from the log (fold). Crash-tail repair closes any step left
        running. Legacy pipelines (no event log) load as-is and seed the log.
        """
        path = Path(filepath)
        log_path = path.with_suffix(".events.jsonl")

        if not path.exists():
            # Projection lost (crash): rebuild from the event log if present.
            if log_path.exists():
                log = PipelineEventLog(log_path)
                events = log.read()
                if events:
                    _repair_crash_tail(log, events)
                    events = log.read()
                    state = project_state(events)
                    pipeline = cls(state, pipelines_dir=str(path.parent))
                    pipeline._log = log
                    pipeline._last_snapshot = _snapshot_dict(state)
                    pipeline._projection = ProjectionCache(path)
                    return pipeline
            raise PipelineError(f"Pipeline state file not found: {filepath}")

        data = path.read_text()
        state = PipelineState.from_json(data)
        pipelines_dir = str(path.parent)

        log = PipelineEventLog(log_path)
        events = log.read()

        if not events:
            # Backward-compat: seed the log from the existing projection (additive).
            snapshot = _snapshot_dict(state)
            ev = log.append("seeded", {"state": snapshot})
            pipeline = cls(state, pipelines_dir=pipelines_dir)
            pipeline._log = log
            pipeline._last_snapshot = snapshot
            pipeline._projection = ProjectionCache(path)
            pipeline._projection.write(state, ev.seq, mandatory=True)
            return pipeline

        _repair_crash_tail(log, events)
        events = log.read()

        projection = ProjectionCache(path)
        proj_state = projection.read(events)
        if proj_state is None:
            proj_state = project_state(events)

        pipeline = cls(proj_state, pipelines_dir=pipelines_dir)
        pipeline._log = log
        pipeline._last_snapshot = _snapshot_dict(proj_state)
        pipeline._projection = projection
        return pipeline

    def _default_dir(self) -> Path:
        return _default_pipelines_dir()

    def _state_path(self) -> Path:
        return self._dir / f"{self.state.id}.json"

    def _log_path(self) -> Path:
        return self._dir / f"{self.state.id}.events.jsonl"

    def _get_log(self) -> PipelineEventLog:
        if self._log is None:
            self._log = PipelineEventLog(self._log_path())
        return self._log

    def _get_projection(self) -> ProjectionCache:
        if self._projection is None:
            self._projection = ProjectionCache(self._state_path())
        return self._projection

    def _save_state(self) -> None:
        """Persist state: append derived event(s) to the log + write projection.

        The event log is the source of truth. Each save diffs the current state
        against the last snapshot and appends the resulting step/status/context
        events; the projection (``{id}.json``) is flushed immediately on
        mandatory events (step_completed/failed/paused) and throttled otherwise.
        The first save seeds the log with a full snapshot so the fold can
        reconstruct identity (additive migration for legacy pipelines).
        """
        self.state.updated_at = datetime.now(timezone.utc).isoformat()
        self._dir.mkdir(parents=True, exist_ok=True)

        log = self._get_log()
        current = _snapshot_dict(self.state)

        if log.tail() is None or self._last_snapshot is None:
            ev = log.append("seeded", {"state": current})
            self._last_snapshot = current
            self._get_projection().write(self.state, ev.seq, mandatory=True)
            return

        mandatory = False
        for event_type, payload in _diff_events(self._last_snapshot, current):
            log.append(event_type, payload)
            if event_type in _MANDATORY_EVENT_TYPES:
                mandatory = True
        self._last_snapshot = current
        tail = log.tail()
        last_seq = tail.seq if tail is not None else 0
        self._get_projection().write(self.state, last_seq, mandatory=mandatory)

    def close(self) -> None:
        """Flush + close the underlying event log (idempotent)."""
        if self._log is not None:
            self._log.close()

    def _next_pending_step(self) -> Optional[str]:
        """Return the first step still pending or failed."""
        for name in self.STEPS:
            st = self.state.steps.get(name)
            if st and st.status in ("pending", "failed"):
                return name
        return None

    def run(
        self,
        search_fn: Optional[Callable] = None,
        review_callback: Optional[Callable] = None,
        skip_search: bool = False,
    ) -> PipelineState:
        """Execute all steps from the first pending one.

        Args:
            search_fn: Callable(sub_question, query) -> List[Dict] for web search.
                       Required unless skip_search=True or raw_findings already in context.
            review_callback: Callable(state) -> bool for human review approval.
                             Returns True to approve, False to reject.
                             If omitted, review step is auto-approved.
            skip_search: If True, the search step is deliberately skipped.
                         Use when findings are pre-loaded or search is handled externally.

        Raises:
            PipelineError: If search_fn is None and skip_search is False
                          and raw_findings is not already in context.
        """
        if not skip_search and search_fn is None and "raw_findings" not in self.state.context:
            raise PipelineError(
                "search_fn is required for the search step. "
                "Pass a search function, set skip_search=True, or pre-load raw_findings in context."
            )
        self._search_fn = search_fn
        self._skip_search = skip_search
        self.state.status = "running"
        self._save_state()

        while True:
            step_name = self._next_pending_step()
            if step_name is None:
                self.state.status = "completed"
                self._save_state()
                logger.info(f"Pipeline {self.state.id}: all steps completed")
                break

            # Execute step with retry
            step = self.state.steps[step_name]
            step.status = "running"
            step.started_at = datetime.now(timezone.utc).isoformat()
            step.attempts += 1
            self._save_state()

            try:
                result = self._execute_step(step_name, search_fn, review_callback)
                step.status = "completed"
                step.result = result
                step.completed_at = datetime.now(timezone.utc).isoformat()
                self._save_state()
                logger.info(f"Pipeline {self.state.id}: step '{step_name}' completed")

            except PipelinePausedError:
                step.status = "paused"
                self.state.status = "awaiting_review"
                self._save_state()
                logger.info(f"Pipeline {self.state.id}: paused at '{step_name}' for review")
                raise  # re-raise so caller knows we paused

            except Exception as e:
                step.last_error = str(e)
                if step.attempts < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** (step.attempts - 1))
                    logger.warning(
                        f"Pipeline {self.state.id}: step '{step_name}' "
                        f"failed (attempt {step.attempts}/{MAX_RETRIES}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    step.status = "failed"
                    self._save_state()
                    # Loop continues, _next_pending_step will re-pick this step
                    continue
                else:
                    step.status = "failed"
                    self.state.status = "failed"
                    self._save_state()
                    raise StepFailedError(
                        f"Step '{step_name}' failed after {MAX_RETRIES} attempts: {e}"
                    ) from e

        return self.state

    def resume(
        self,
        search_fn: Optional[Callable] = None,
        review_callback: Optional[Callable] = None,
        skip_search: bool = False,
    ) -> PipelineState:
        """Resume a paused or failed pipeline from its last checkpoint.

        Same signature as run(). Picks up from the first pending/failed step.
        On resume, if the pipeline has raw_findings from a previous partial run,
        search_fn is not required (skip_search is auto-detected).
        """
        # If raw_findings exist from a prior run, search can be skipped
        if not skip_search and search_fn is None and "raw_findings" in self.state.context:
            skip_search = True

        # Reset status from paused/failed to running for retry
        if self.state.status in ("awaiting_review", "failed"):
            next_step = self._next_pending_step()
            if next_step:
                step = self.state.steps[next_step]
                if step.status == "paused":
                    pass
                elif step.status == "failed":
                    step.attempts = 0
            self.state.status = "running"
            self._save_state()

        return self.run(search_fn=search_fn, review_callback=review_callback, skip_search=skip_search)

    def _execute_step(
        self,
        step_name: str,
        search_fn: Optional[Callable] = None,
        review_callback: Optional[Callable] = None,
    ) -> Any:
        """Dispatch to the appropriate step handler."""
        handlers: Dict[str, Callable] = {
            "plan": self._step_plan,
            "search": lambda: self._step_search(search_fn),
            "structure": self._step_structure,
            "cross_ref": self._step_cross_ref,
            "synthesize": self._step_synthesize,
            "review": lambda: self._step_review(review_callback),
            "persist": self._step_persist,
        }
        handler = handlers.get(step_name)
        if handler is None:
            raise PipelineError(f"Unknown step: {step_name}")
        return handler()

    # ── Step Implementations ──────────────────────────────────────────────

    def _step_plan(self) -> dict:
        """Decompose the research question."""
        from ai_kos.deep_research import plan_research
        plan = plan_research(self.state.question)
        self.state.context["plan"] = asdict(plan)
        self.state.context["sub_questions"] = plan.sub_questions
        self.state.context["search_queries"] = plan.search_queries
        self.state.context["perspectives"] = plan.perspectives
        return asdict(plan)

    def _step_search(self, search_fn: Optional[Callable]) -> list:
        """Execute web searches for each sub-question."""
        if getattr(self, '_skip_search', False):
            logger.info("Pipeline: search step deliberately skipped (skip_search=True)")
            if "raw_findings" not in self.state.context:
                self.state.context["raw_findings"] = []
            return self.state.context.get("raw_findings", [])

        if search_fn is None:
            raise PipelineError(
                "search_fn is required — pass a search function or set skip_search=True"
            )

        sub_questions = self.state.context.get("sub_questions", [])
        queries = self.state.context.get("search_queries", [])
        all_findings = []

        for idx, (sq, query) in enumerate(zip(sub_questions, queries)):
            try:
                results = search_fn(sq, query)
                for r in results:
                    r["sub_question_idx"] = idx
                    all_findings.append(r)
            except Exception as e:
                logger.warning(f"Pipeline: search failed for sub-question {idx}: {e}")
                # Continue with other sub-questions

        self.state.context["raw_findings"] = all_findings
        return all_findings

    def _step_structure(self) -> list:
        """Structure raw search results into typed findings."""
        from ai_kos.deep_research import structure_findings

        raw = self.state.context.get("raw_findings", [])
        if not raw:
            logger.warning("Pipeline: no raw findings to structure")
            self.state.context["structured_findings"] = []
            return []

        structured = structure_findings(raw)
        self.state.context["structured_findings"] = [
            {
                "sub_question_idx": f.sub_question_idx,
                "source_url": f.source_url,
                "source_title": f.source_title,
                "key_claim": f.key_claim,
                "evidence": f.evidence,
                "confidence": f.confidence,
            }
            for f in structured
        ]
        return self.state.context["structured_findings"]

    def _step_cross_ref(self) -> list:
        """Cross-reference findings against AI-KOS knowledge base."""
        from ai_kos.deep_research import SourceFinding, cross_reference_with_knowledge

        structured = self.state.context.get("structured_findings", [])
        if not structured:
            self.state.context["cross_references"] = []
            return []

        findings = [
            SourceFinding(
                sub_question_idx=f["sub_question_idx"],
                source_url=f["source_url"],
                source_title=f["source_title"],
                key_claim=f["key_claim"],
                evidence=f.get("evidence", ""),
                confidence=f.get("confidence", "medium"),
            )
            for f in structured
        ]

        refs = cross_reference_with_knowledge(findings)
        self.state.context["cross_references"] = [
            {
                "finding": r.finding,
                "existing_article": r.existing_article,
                "relationship": r.relationship,
                "notes": r.notes,
            }
            for r in refs
        ]
        return self.state.context["cross_references"]

    def _step_synthesize(self) -> dict:
        """Generate synthesis report."""
        from ai_kos.deep_research import ResearchResult, synthesize_report

        findings = self.state.context.get("structured_findings", [])
        cross_refs = self.state.context.get("cross_references", [])
        sub_questions = self.state.context.get("sub_questions", [])

        result = ResearchResult(
            id=self.state.id,
            plan_id=self.state.id,
            question=self.state.question,
            sub_questions=sub_questions,
            findings=findings,
            cross_references=cross_refs,
            synthesis="",
            knowledge_gaps=[],
        )

        # Generate base synthesis (LLM fills in the actual synthesis text later)
        report = synthesize_report(result)
        self.state.context["synthesis_report"] = report
        self.state.context["research_result"] = {
            "question": self.state.question,
            "sub_questions": sub_questions,
            "findings": findings,
            "cross_references": cross_refs,
            "synthesis": "",
            "knowledge_gaps": [],
        }
        return {"report": report, "result": self.state.context["research_result"]}

    def _step_review(self, review_callback: Optional[Callable] = None) -> str:
        """Human review gate. Pauses pipeline if no callback auto-approves."""
        if review_callback is None:
            logger.info("Pipeline: no review_callback — auto-approving")
            return "auto_approved"

        approved = review_callback(self.state)
        if not approved:
            raise PipelinePausedError("Human review rejected — pipeline paused")

        return "approved"

    def _step_persist(self) -> dict:
        """Persist findings as AI-KOS articles."""
        from ai_kos.deep_research import ResearchResult, persist_research

        rr_data = self.state.context.get("research_result", {})
        if not rr_data:
            raise PipelineError("No research result to persist")

        result = ResearchResult(
            id=self.state.id,
            plan_id=self.state.id,
            question=rr_data["question"],
            sub_questions=rr_data.get("sub_questions", []),
            findings=rr_data.get("findings", []),
            cross_references=rr_data.get("cross_references", []),
            synthesis=rr_data.get("synthesis", ""),
            knowledge_gaps=rr_data.get("knowledge_gaps", []),
        )

        knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
        created = persist_research(result, knowledge_dir=knowledge_dir)

        self.state.context["persisted"] = created
        return created

    # ── Inspection ─────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a human-readable summary of pipeline state."""
        steps_summary = {}
        for name in self.STEPS:
            st = self.state.steps.get(name)
            if st:
                steps_summary[name] = {
                    "status": st.status,
                    "attempts": st.attempts,
                    "last_error": st.last_error,
                }
        return {
            "id": self.state.id,
            "question": self.state.question,
            "status": self.state.status,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "steps": steps_summary,
        }

    @staticmethod
    def list_pipelines(pipelines_dir: Optional[str] = None) -> List[Dict]:
        """List all saved pipeline states."""
        d = Path(pipelines_dir) if pipelines_dir else _default_pipelines_dir()
        if not d.exists():
            return []
        results = []
        for f in sorted(d.glob("*.json")):
            try:
                state = PipelineState.from_json(f.read_text())
                results.append({
                    "id": state.id,
                    "question": state.question[:120],
                    "status": state.status,
                    "updated_at": state.updated_at,
                })
            except Exception:
                continue
        return results
