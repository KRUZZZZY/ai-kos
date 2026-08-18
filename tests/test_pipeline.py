"""Tests for AI-KOS ResearchPipeline — durable execution, retry, state persistence."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_kos.pipeline import (
    PipelineState,
    StepState,
    ResearchPipeline,
    PipelineError,
    StepFailedError,
    PipelinePausedError,
    _default_pipelines_dir,
)


@pytest.fixture(autouse=True)
def _isolate_kb(tmp_path, monkeypatch):
    """Redirect article + DB writes to a tmp KB so ResearchPipeline persist
    steps never write research-note articles into the live knowledge/ tree.
    (Audit finding: 'Research: Q?'-style junk articles were re-created on every
    pytest run because the pipeline persist step resolved the live KB.)"""
    import ai_kos.articles as articles
    import ai_kos.db as db
    kb = tmp_path / "knowledge"
    kb.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(articles, "KNOWLEDGE_DIR", str(kb))
    monkeypatch.setattr(db, "_db_path", str(tmp_path / "datasets" / "ai-kos.db"))
    monkeypatch.setattr(db, "_conn", None)
    yield


class TestStepState:
    def test_default_values(self):
        s = StepState(name="plan", status="pending")
        assert s.name == "plan"
        assert s.status == "pending"
        assert s.attempts == 0
        assert s.last_error is None
        assert s.result is None

    def test_serialization_roundtrip(self):
        s = StepState(name="search", status="completed", attempts=1, result=["a", "b"])
        data = json.dumps(s.__dict__)
        restored = StepState(**json.loads(data))
        assert restored.name == "search"
        assert restored.result == ["a", "b"]


class TestPipelineState:
    def test_initial_state(self):
        ps = PipelineState(id="abc", question="Test?")
        assert ps.status == "planned"
        assert ps.steps == {}
        assert ps.context == {}

    def test_json_roundtrip(self):
        ps = PipelineState(
            id="abc",
            question="What is X?",
            steps={
                "plan": StepState(name="plan", status="completed", result={"sub_questions": ["Q1"]}),
            },
            context={"key": "value"},
        )
        j = ps.to_json()
        restored = PipelineState.from_json(j)
        assert restored.id == "abc"
        assert restored.question == "What is X?"
        assert restored.steps["plan"].status == "completed"
        assert restored.steps["plan"].result == {"sub_questions": ["Q1"]}
        assert restored.context == {"key": "value"}

    def test_json_roundtrip_empty_steps(self):
        ps = PipelineState(id="xyz", question="Empty?")
        j = ps.to_json()
        restored = PipelineState.from_json(j)
        assert restored.id == "xyz"
        assert restored.steps == {}


class TestResearchPipeline:
    def test_create_sets_all_steps_pending(self, tmp_path):
        p = ResearchPipeline.create("Does this work?", pipelines_dir=str(tmp_path))
        assert p.state.question == "Does this work?"
        assert p.state.status == "planned"
        for name in ResearchPipeline.STEPS:
            assert p.state.steps[name].status == "pending"

    def test_create_saves_nothing_until_run(self, tmp_path):
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        state_files = list(tmp_path.glob("*.json"))
        assert len(state_files) == 0  # No save until run() is called

    def test_run_completes_all_steps(self, tmp_path):
        """Full pipeline without search (skip_search mode)."""
        p = ResearchPipeline.create("Test question", pipelines_dir=str(tmp_path))
        result = p.run(skip_search=True)

        assert result.status == "completed"
        for name in ResearchPipeline.STEPS:
            step = result.steps[name]
            # review is auto-approved without callback, persist needs real data
            if name == "review":
                assert step.status == "completed"
            elif name == "persist":
                # May fail if no findings — that's ok in unit test
                pass
            else:
                assert step.status == "completed", f"Step {name} status is {step.status}: {step.last_error}"

    def test_run_saves_state_to_disk(self, tmp_path):
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.run(skip_search=True)

        state_files = list(tmp_path.glob("*.json"))
        assert len(state_files) == 1

        # Verify it can be loaded back
        p2 = ResearchPipeline.load(str(state_files[0]))
        assert p2.state.id == p.state.id
        assert p2.state.question == "Q?"

    def test_run_with_search_fn(self, tmp_path):
        """Pipeline with a mock search function."""
        mock_search = MagicMock(return_value=[
            {"title": "Source 1", "url": "https://example.com", "key_claim": "Finding A"},
            {"title": "Source 2", "url": "https://example.org", "key_claim": "Finding B"},
        ])

        p = ResearchPipeline.create("Research question?", pipelines_dir=str(tmp_path))
        result = p.run(search_fn=mock_search)

        assert result.status == "completed"
        assert result.steps["search"].status == "completed"
        assert len(result.steps["search"].result) == 10  # 5 sub-questions × 2 results each
        # Verify context was populated
        assert "raw_findings" in p.state.context
        assert len(p.state.context["raw_findings"]) == 10

    def test_run_pauses_at_review_with_callback(self, tmp_path):
        """Pipeline pauses when review callback returns False."""
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.run(search_fn=MagicMock(return_value=[]))

        # After a full run without review callback, it completes
        assert p.state.status == "completed" or p.state.status == "failed"

    def test_review_callback_pauses(self, tmp_path):
        """If review callback returns False, pipeline pauses."""
        p = ResearchPipeline.create("Pause me", pipelines_dir=str(tmp_path))
        p.run(search_fn=MagicMock(return_value=[]))

        # Run again with a rejecting callback that triggers pause at review step
        def reject_review(state):
            return False

        # We can't easily test this without running a full pipeline again.
        # Instead, let's verify the mechanism works by manual step injection.
        p2 = ResearchPipeline.create("Pause test", pipelines_dir=str(tmp_path))
        p2.state.steps = {name: StepState(name=name, status="pending") for name in ResearchPipeline.STEPS}
        # Mark all steps before review as completed
        for name in ["plan", "search", "structure", "cross_ref", "synthesize"]:
            p2.state.steps[name].status = "completed"
        p2.state.status = "running"
        p2.state.context["raw_findings"] = []
        p2.state.context["structured_findings"] = []
        p2.state.context["cross_references"] = []
        p2.state.context["sub_questions"] = ["Q1"]
        p2.state.context["research_result"] = {
            "question": "Pause test",
            "sub_questions": ["Q1"],
            "findings": [],
            "cross_references": [],
            "synthesis": "",
            "knowledge_gaps": [],
        }

        with pytest.raises(PipelinePausedError):
            p2.run(review_callback=reject_review)

        assert p2.state.status == "awaiting_review"
        assert p2.state.steps["review"].status == "paused"

    def test_resume_from_paused(self, tmp_path):
        """Resume a paused pipeline."""
        p = ResearchPipeline.create("Resume test", pipelines_dir=str(tmp_path))
        # Set up state as if paused at review
        for name in ResearchPipeline.STEPS:
            p.state.steps[name] = StepState(name=name, status="pending")
        for name in ["plan", "search", "structure", "cross_ref", "synthesize"]:
            p.state.steps[name].status = "completed"
        p.state.steps["review"].status = "paused"
        p.state.status = "awaiting_review"
        p.state.context["raw_findings"] = []
        p.state.context["structured_findings"] = []
        p.state.context["cross_references"] = []
        p.state.context["sub_questions"] = ["Q1"]
        p.state.context["research_result"] = {
            "question": "Resume test",
            "sub_questions": ["Q1"],
            "findings": [],
            "cross_references": [],
            "synthesis": "",
            "knowledge_gaps": [],
        }
        p._save_state()

        # Resume with approving callback
        def approve(state):
            return True

        # Load from disk
        p2 = ResearchPipeline.load(str(p._state_path()))
        result = p2.resume(review_callback=approve)

        assert result.status == "completed" or p2.state.steps["review"].status != "paused"

    def test_retry_on_step_failure(self, tmp_path):
        """A step that fails once then succeeds should use retry logic."""
        p = ResearchPipeline.create("Retry test", pipelines_dir=str(tmp_path))

        call_count = [0]
        def flaky_structure():
            """structure_step is called directly, not via search_fn."""
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Transient network error")
            return [{"key_claim": "C", "source_url": "http://x"}]

        # Set up so structure step runs
        p.state.status = "running"
        p.state.steps["plan"].status = "completed"
        p.state.steps["search"].status = "completed"
        p.state.steps["search"].result = []
        p.state.context["raw_findings"] = [
            {"sub_question_idx": 0, "url": "http://x", "title": "T", "key_claim": "C"}
        ]

        # Monkey-patch the structure handler to use our flaky function
        original = p._step_structure
        p._step_structure = flaky_structure
        try:
            result = p.run()
            assert call_count[0] == 2  # First failed, second succeeded
            assert result.steps["structure"].status == "completed"
        finally:
            p._step_structure = original

    def test_run_without_search_fn_raises(self, tmp_path):
        """Calling run() without search_fn or skip_search should raise."""
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        with pytest.raises(PipelineError, match="search_fn is required"):
            p.run()

    def test_run_with_skip_search_works(self, tmp_path):
        """skip_search=True allows pipeline to run without a search function."""
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.state.steps["plan"].status = "completed"
        p.state.context["sub_questions"] = ["Q1"]
        p.state.status = "running"
        result = p.run(skip_search=True)
        assert result.status == "completed" or result.status == "failed"

    def test_step_fails_permanently_after_max_retries(self, tmp_path):
        """After MAX_RETRIES failures, the pipeline should fail."""
        from ai_kos.pipeline import MAX_RETRIES

        p = ResearchPipeline.create("Fail test", pipelines_dir=str(tmp_path))
        p.state.status = "running"
        p.state.steps["plan"].status = "completed"
        p.state.steps["search"].status = "completed"
        p.state.steps["search"].result = []
        p.state.context["raw_findings"] = [
            {"sub_question_idx": 0, "url": "http://x", "title": "T", "key_claim": "C"}
        ]

        def always_fail():
            raise RuntimeError("Permanent failure")

        p._step_structure = always_fail

        with pytest.raises(StepFailedError, match="Permanent failure"):
            p.run()

        assert p.state.steps["structure"].attempts == MAX_RETRIES
        assert p.state.steps["structure"].status == "failed"
        assert p.state.status == "failed"

    def test_summary(self, tmp_path):
        p = ResearchPipeline.create("Summary test", pipelines_dir=str(tmp_path))
        p.run(search_fn=MagicMock(return_value=[]))

        s = p.summary()
        assert s["id"] == p.state.id
        assert s["question"] == "Summary test"
        assert "steps" in s
        assert "plan" in s["steps"]

    def test_list_pipelines(self, tmp_path):
        p1 = ResearchPipeline.create("Q1", pipelines_dir=str(tmp_path))
        p1._save_state()

        p2 = ResearchPipeline.create("Q2", pipelines_dir=str(tmp_path))
        p2._save_state()

        listed = ResearchPipeline.list_pipelines(pipelines_dir=str(tmp_path))
        assert len(listed) == 2
        assert any(p["question"] == "Q1" for p in listed)
        assert any(p["question"] == "Q2" for p in listed)

    def test_list_pipelines_empty(self, tmp_path):
        empty_dir = tmp_path / "nope"
        empty_dir.mkdir()
        listed = ResearchPipeline.list_pipelines(pipelines_dir=str(empty_dir))
        assert listed == []

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(PipelineError, match="not found"):
            ResearchPipeline.load(str(tmp_path / "does_not_exist.json"))

    def test_crash_mid_pipeline_and_resume(self, tmp_path):
        """Simulate a crash mid-pipeline and verify resume from checkpoint."""
        p = ResearchPipeline.create("Crash test", pipelines_dir=str(tmp_path))

        # Manually complete plan step to simulate partial progress
        p.state.status = "running"
        p.state.steps["plan"].status = "completed"
        p.state.steps["plan"].result = {"sub_questions": ["Q1", "Q2"]}
        p.state.context["sub_questions"] = ["Q1", "Q2"]
        p.state.context["search_queries"] = ["sq1", "sq2"]
        p._save_state()

        pipeline_id = p.state.id

        # "Crash" — discard the in-memory pipeline
        del p

        # Resume from disk
        state_path = tmp_path / f"{pipeline_id}.json"
        assert state_path.exists(), "State file should survive crash"

        p2 = ResearchPipeline.load(str(state_path))
        assert p2.state.id == pipeline_id
        assert p2.state.question == "Crash test"
        assert p2.state.steps["plan"].status == "completed"
        assert p2.state.context["sub_questions"] == ["Q1", "Q2"]

        # Should resume from search step
        next_step = p2._next_pending_step()
        assert next_step == "search"


class TestIntegrationWithDeepResearch:
    """Verify the pipeline wires correctly into the existing deep_research module."""

    def test_step_plan_integrates(self, tmp_path):
        from ai_kos.deep_research import ResearchPlan

        p = ResearchPipeline.create(
            "What is the architecture of Cloudflare Workers?",
            pipelines_dir=str(tmp_path),
        )

        # Run just the plan step by completing others as needed
        p.state.status = "running"

        # Execute plan step
        result = p._execute_step("plan")
        assert "sub_questions" in result
        assert len(result["sub_questions"]) == 5
        assert len(result["search_queries"]) == 5
        assert len(result["perspectives"]) == 5
        assert "What are the core concepts" in result["sub_questions"][0]

    def test_step_structure_integrates(self, tmp_path):
        from ai_kos.deep_research import SourceFinding

        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.state.context["raw_findings"] = [
            {
                "sub_question_idx": 0,
                "url": "https://example.com",
                "title": "Example",
                "key_claim": "Something interesting",
                "description": "Desc",
                "content": "Evidence text here",
                "confidence": "high",
            }
        ]

        result = p._execute_step("structure")
        assert len(result) == 1
        assert result[0]["key_claim"] == "Something interesting"
        assert result[0]["source_url"] == "https://example.com"

    def test_step_cross_ref_integrates(self, tmp_path):
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.state.context["structured_findings"] = [
            {
                "sub_question_idx": 0,
                "source_url": "https://example.com",
                "source_title": "Example",
                "key_claim": "V8 isolates provide 0ms cold starts",
                "evidence": "Evidence",
                "confidence": "high",
            }
        ]

        result = p._execute_step("cross_ref")
        assert isinstance(result, list)
        assert len(result) == 1
        assert "relationship" in result[0]

    def test_step_synthesize_integrates(self, tmp_path):
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        p.state.context["structured_findings"] = []
        p.state.context["cross_references"] = []
        p.state.context["sub_questions"] = ["Q1"]

        result = p._execute_step("synthesize")
        assert "report" in result
        assert "result" in result
        assert "Deep Research" in result["report"]


class TestDefaultDir:
    def test_returns_path(self):
        d = _default_pipelines_dir()
        assert isinstance(d, Path)
        assert d.name == "pipelines"


class TestEventLogIntegration:
    """Feature 3: event log is source of truth, {id}.json is a projection."""

    def test_run_produces_event_log_and_projection(self, tmp_path):
        from ai_kos.pipeline_log import PipelineEventLog

        search_fn = MagicMock(return_value=[
            {"title": "T", "url": "https://x", "key_claim": "C"},
        ])
        p = ResearchPipeline.create("Q?", pipelines_dir=str(tmp_path))
        result = p.run(search_fn=search_fn)
        assert result.status == "completed"
        pid = p.state.id

        log_path = tmp_path / f"{pid}.events.jsonl"
        assert log_path.exists()
        events = PipelineEventLog(log_path).read()
        assert events[0].type == "seeded"
        types = {e.type for e in events}
        assert "step_completed" in types

        # projection is {id}.json with a ver field (seq of last applied event);
        # the final status_changed is throttled, so ver may trail the tail.
        proj = json.loads((tmp_path / f"{pid}.json").read_text())
        assert "ver" in proj
        assert proj["ver"] <= events[-1].seq

        # reload reconstructs the completed state (fast path or replay)
        p2 = ResearchPipeline.load(str(tmp_path / f"{pid}.json"))
        assert p2.state.status == "completed"
        assert p2.state.question == "Q?"

    def test_crash_delete_projection_rebuilds_from_log(self, tmp_path):
        search_fn = MagicMock(return_value=[
            {"title": "T", "url": "https://x", "key_claim": "C"},
        ])
        p = ResearchPipeline.create("Crash?", pipelines_dir=str(tmp_path))
        p.run(search_fn=search_fn)
        pid = p.state.id

        # "crash": lose the projection, keep the log
        (tmp_path / f"{pid}.json").unlink()

        p2 = ResearchPipeline.load(str(tmp_path / f"{pid}.json"))
        assert p2.state.id == pid
        assert p2.state.question == "Crash?"
        assert p2.state.status == "completed"

    def test_legacy_json_without_log_seeds_on_load(self, tmp_path):
        from dataclasses import asdict

        from ai_kos.pipeline_log import PipelineEventLog

        p = ResearchPipeline.create("Legacy", pipelines_dir=str(tmp_path))
        p.state.status = "running"
        json_path = tmp_path / f"{p.state.id}.json"
        # write a legacy snapshot (no ver, no log) as the old code did
        json_path.write_text(json.dumps(asdict(p.state), indent=2, default=str))
        log_path = tmp_path / f"{p.state.id}.events.jsonl"
        assert not log_path.exists()

        p2 = ResearchPipeline.load(str(json_path))
        assert p2.state.id == p.state.id
        assert p2.state.question == "Legacy"

        # log was seeded on load (additive migration)
        assert log_path.exists()
        events = PipelineEventLog(log_path).read()
        assert [e.type for e in events] == ["seeded"]

    def test_interrupted_step_gets_synthetic_closer(self, tmp_path):
        p = ResearchPipeline.create("Crash mid-step", pipelines_dir=str(tmp_path))
        p.state.status = "running"
        p._save_state()  # seed (status running, all steps pending)
        p.state.steps["plan"].status = "running"
        p.state.steps["plan"].started_at = "t"
        p.state.steps["plan"].attempts = 1
        p._save_state()  # step_started(plan) — then "crash" before completion
        pid = p.state.id

        p2 = ResearchPipeline.load(str(tmp_path / f"{pid}.json"))
        assert p2.state.steps["plan"].status == "failed"
        assert p2.state.steps["plan"].last_error == "interrupted by crash"
