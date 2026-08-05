"""AI-KOS ResearchPipeline — durable execution engine for deep research.

Adopts Cloudflare Workflows' step-based durable execution pattern:
- Each step is wrapped with retry + exponential backoff
- Pipeline state persisted to JSON after each step
- Pause/resume across Hermes sessions
- Human review gate before article creation

Built with zero external dependencies (json + pathlib only).
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

logger = logging.getLogger("ai-kos.pipeline")

PIPELINE_DIR_NAME = "pipelines"
MAX_RETRIES = 3
BASE_DELAY = 2  # seconds, doubles each retry


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
        steps = {}
        for name, s in raw.get("steps", {}).items():
            steps[name] = StepState(**s)
        raw["steps"] = steps
        return cls(**raw)


def _default_pipelines_dir() -> Path:
    knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
    return Path(knowledge_dir) / PIPELINE_DIR_NAME


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
        """Resume a pipeline from its JSON state file."""
        path = Path(filepath)
        if not path.exists():
            raise PipelineError(f"Pipeline state file not found: {filepath}")
        data = path.read_text()
        state = PipelineState.from_json(data)
        return cls(state, pipelines_dir=str(path.parent))

    def _default_dir(self) -> Path:
        return _default_pipelines_dir()

    def _state_path(self) -> Path:
        return self._dir / f"{self.state.id}.json"

    def _save_state(self) -> None:
        """Persist pipeline state to disk atomically."""
        self.state.updated_at = datetime.now(timezone.utc).isoformat()
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = self._state_path().with_suffix(".tmp")
        tmp.write_text(self.state.to_json())
        tmp.replace(self._state_path())

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
    ) -> PipelineState:
        """Execute all steps from the first pending one.

        Args:
            search_fn: Callable(sub_question, query) -> List[Dict] for web search.
                       If omitted, search step is skipped (caller does it externally).
            review_callback: Callable(state) -> bool for human review approval.
                             Returns True to approve, False to reject.
                             If omitted, review step is auto-approved.
        """
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
    ) -> PipelineState:
        """Resume a paused or failed pipeline from its last checkpoint.

        Same signature as run(). Picks up from the first pending/failed step.
        """
        # Reset status from paused/failed to running for retry
        if self.state.status in ("awaiting_review", "failed"):
            # Find the step we're resuming from
            next_step = self._next_pending_step()
            if next_step:
                step = self.state.steps[next_step]
                if step.status == "paused":
                    # Review step — proceed with existing review_callback
                    pass
                elif step.status == "failed":
                    # Reset attempts for a fresh retry cycle on resume
                    step.attempts = 0
            self.state.status = "running"
            self._save_state()

        return self.run(search_fn=search_fn, review_callback=review_callback)

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
        if search_fn is None:
            logger.info("Pipeline: no search_fn provided — skipping search step")
            if "raw_findings" not in self.state.context:
                self.state.context["raw_findings"] = []
            return self.state.context.get("raw_findings", [])

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
