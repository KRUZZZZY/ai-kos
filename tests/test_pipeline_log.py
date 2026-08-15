"""Tests for ai_kos.pipeline_log — pipeline event log + projection cache (Feature 3).

Covers the append-only event log (source of truth) and the write-behind
projection cache: contiguous seq, torn-tail repair, durable-before-return,
crash-tail synthetic closers, and the pure project_state fold.
"""

import json
from pathlib import Path

import pytest

from ai_kos.pipeline import PipelineState, StepState
from ai_kos.pipeline_log import (
    PipelineEvent,
    PipelineEventLog,
    ProjectionCache,
    project_state,
    EventLogError,
    EventLogCorruptError,
)


def _ev(seq, type_, payload=None):
    """Build a PipelineEvent with a fixed, valid ISO timestamp."""
    return PipelineEvent(
        seq=seq,
        type=type_,
        at=f"2026-08-15T00:00:{seq:02d}+00:00",
        payload=payload if payload is not None else {},
    )


def _state(step_statuses=None):
    """A minimal running PipelineState with plan/search steps."""
    state = PipelineState(id="abc", question="Q?")
    state.status = "running"
    state.steps = {
        name: StepState(
            name=name,
            status=(step_statuses or {}).get(name, "pending"),
        )
        for name in ("plan", "search")
    }
    return state


class TestPipelineEvent:
    def test_roundtrip(self):
        ev = PipelineEvent(seq=3, type="step_started", at="t", payload={"step": "plan"})
        restored = PipelineEvent.from_line(ev.to_json())
        assert restored.seq == 3
        assert restored.type == "step_started"
        assert restored.at == "t"
        assert restored.payload == {"step": "plan"}


class TestPipelineEventLog:
    def test_append_contiguous_seq_and_durable(self, tmp_path):
        log = PipelineEventLog(tmp_path / "p.events.jsonl")
        e1 = log.append("step_started", {"step": "plan"})
        e2 = log.append("step_completed", {"step": "plan", "result": {}})
        assert e1.seq == 1
        assert e2.seq == 2
        # durable-before-return: file exists immediately with both lines
        p = tmp_path / "p.events.jsonl"
        assert p.exists()
        lines = p.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["seq"] == 1
        assert json.loads(lines[1])["seq"] == 2

    def test_read_from_suffix_only(self, tmp_path):
        log = PipelineEventLog(tmp_path / "p.events.jsonl")
        for i in range(1, 6):
            log.append("status_changed", {"status": f"s{i}"})
        assert [e.seq for e in log.read_from(3)] == [4, 5]
        assert log.read_from(5) == []
        assert [e.seq for e in log.read()] == [1, 2, 3, 4, 5]

    def test_tail(self, tmp_path):
        log = PipelineEventLog(tmp_path / "p.events.jsonl")
        assert log.tail() is None
        log.append("status_changed", {"status": "x"})
        assert log.tail().seq == 1

    def test_torn_tail_repaired_on_open(self, tmp_path):
        p = tmp_path / "p.events.jsonl"
        p.write_text(
            '{"seq": 1, "type": "a", "at": "t", "payload": {}}\n'
            '{"seq": 2, "type": "b", "at": "t", "payload": {"tor'
        )
        log = PipelineEventLog(p)  # __init__ repairs the torn final line
        assert [e.seq for e in log.read()] == [1]
        assert log.tail().seq == 1

    def test_mid_log_corruption_raises(self, tmp_path):
        p = tmp_path / "p.events.jsonl"
        p.write_text(
            '{"seq": 1, "type": "a", "at": "t", "payload": {}}\n'
            'GARBAGE\n'
            '{"seq": 2, "type": "b", "at": "t", "payload": {}}\n'
        )
        with pytest.raises(EventLogCorruptError):
            PipelineEventLog(p)

    def test_non_serializable_payload_raises(self, tmp_path):
        log = PipelineEventLog(tmp_path / "p.events.jsonl")
        with pytest.raises(EventLogError):
            log.append("context_updated", {"bad": {1, 2, 3}})

    def test_append_after_reopen_is_contiguous(self, tmp_path):
        p = tmp_path / "p.events.jsonl"
        log1 = PipelineEventLog(p)
        log1.append("step_started", {"step": "plan"})
        log1.close()
        log2 = PipelineEventLog(p)
        assert log2.append("step_completed", {"step": "plan"}).seq == 2

    def test_close_is_idempotent(self, tmp_path):
        log = PipelineEventLog(tmp_path / "p.events.jsonl")
        log.append("status_changed", {"status": "x"})
        log.close()
        log.close()  # no-op, no raise


class TestProjectState:
    def test_folds_each_event_type(self):
        events = [
            _ev(1, "seeded", {"state": {
                "id": "x", "question": "Q?", "status": "planned",
                "steps": {}, "context": {}, "created_at": "t0",
            }}),
            _ev(2, "status_changed", {"status": "running"}),
            _ev(3, "step_started", {"step": "plan", "started_at": "t1", "attempts": 1}),
            _ev(4, "step_completed", {"step": "plan", "result": {"sub_questions": ["a"]}, "completed_at": "t2"}),
            _ev(5, "step_started", {"step": "search", "attempts": 1}),
            _ev(6, "step_failed", {"step": "search", "last_error": "boom"}),
            _ev(7, "context_updated", {"context": {"raw_findings": []}}),
        ]
        state = project_state(events)
        assert state.id == "x"
        assert state.question == "Q?"
        assert state.status == "running"
        assert state.steps["plan"].status == "completed"
        assert state.steps["plan"].result == {"sub_questions": ["a"]}
        assert state.steps["search"].status == "failed"
        assert state.steps["search"].last_error == "boom"
        assert state.context == {"raw_findings": []}

    def test_step_paused(self):
        events = [
            _ev(1, "seeded", {"state": {"id": "x", "question": "Q", "status": "running", "steps": {}, "context": {}}}),
            _ev(2, "step_started", {"step": "review", "attempts": 1}),
            _ev(3, "step_paused", {"step": "review"}),
        ]
        state = project_state(events)
        assert state.steps["review"].status == "paused"

    def test_interrupted_synthetic_closer(self):
        events = [
            _ev(1, "seeded", {"state": {"id": "x", "question": "Q", "status": "running", "steps": {}, "context": {}}}),
            _ev(2, "step_started", {"step": "search", "attempts": 2}),
            _ev(3, "interrupted", {"step": "search", "status": "failed", "last_error": "interrupted by crash"}),
        ]
        state = project_state(events)
        assert state.steps["search"].status == "failed"
        assert state.steps["search"].last_error == "interrupted by crash"

    def test_base_preserved_and_not_mutated(self):
        base = _state({"plan": "completed"})
        events = [
            _ev(1, "step_started", {"step": "search", "attempts": 1}),
            _ev(2, "step_completed", {"step": "search", "result": [1, 2]}),
        ]
        out = project_state(events, base=base)
        # base is not mutated (pure fold)
        assert base.steps["search"].status == "pending"
        assert out is not base
        assert out.steps["plan"].status == "completed"  # carried from base
        assert out.steps["search"].status == "completed"
        assert out.steps["search"].result == [1, 2]

    def test_requires_seed_or_base(self):
        with pytest.raises(EventLogError):
            project_state([_ev(1, "status_changed", {"status": "x"})])


class TestProjectionCache:
    def test_fast_path_on_matching_ver(self, tmp_path):
        cache = ProjectionCache(tmp_path / "x.json")
        state = _state({"plan": "completed"})
        cache.write(state, seq=3, mandatory=True)
        events = [_ev(1, "x"), _ev(2, "x"), _ev(3, "x")]
        got = cache.read(events)
        assert got is not None
        assert got.id == "abc"
        assert got.steps["plan"].status == "completed"

    def test_discard_and_replay_on_mismatch(self, tmp_path):
        cache = ProjectionCache(tmp_path / "x.json")
        cache.write(_state(), seq=3, mandatory=True)
        events = [_ev(1, "x"), _ev(2, "x"), _ev(3, "x"), _ev(4, "x")]
        assert cache.read(events) is None  # ver 3 != last seq 4 → discard

    def test_missing_file_returns_none(self, tmp_path):
        cache = ProjectionCache(tmp_path / "nope.json")
        assert cache.read([_ev(1, "x")]) is None

    def test_mandatory_write_flushes_immediately(self, tmp_path):
        cache = ProjectionCache(
            tmp_path / "x.json", write_every_events=1000, write_interval_ms=10_000_000
        )
        cache.write(_state(), seq=1, mandatory=True)
        assert (tmp_path / "x.json").exists()

    def test_throttled_write_defers(self, tmp_path):
        # High thresholds → non-mandatory writes are deferred
        cache = ProjectionCache(
            tmp_path / "x.json", write_every_events=1000, write_interval_ms=10_000_000
        )
        cache.write(_state(), seq=1)
        assert not (tmp_path / "x.json").exists()

    def test_write_every_events_trigger(self, tmp_path):
        cache = ProjectionCache(
            tmp_path / "y.json", write_every_events=3, write_interval_ms=10_000_000
        )
        cache.write(_state(), seq=1)
        cache.write(_state(), seq=2)
        assert not (tmp_path / "y.json").exists()
        cache.write(_state(), seq=3)
        assert (tmp_path / "y.json").exists()

    def test_ver_embedded_in_json(self, tmp_path):
        cache = ProjectionCache(tmp_path / "z.json")
        cache.write(_state(), seq=7, mandatory=True)
        data = json.loads((tmp_path / "z.json").read_text())
        assert data["ver"] == 7
