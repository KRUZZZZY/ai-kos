"""Tests for ai_kos.audit — append-only, fsync-before-return audit log."""

import json
import pytest
from unittest.mock import patch


def _entry(**kw):
    base = {"seq": 1, "at": "2026-01-01T00:00:00+00:00", "source": "s",
            "kind": "model_input", "preview": "p", "meta": {}}
    base.update(kw)
    return base


class TestAuditLog:
    def test_append_contiguous_seq(self, tmp_path):
        from ai_kos.audit import AuditLog
        log = AuditLog(tmp_path / "audit.jsonl")
        e1 = log.log("s1", "hello", meta={"a": 1})
        e2 = log.log("s1", "world")
        e3 = log.log("s2", "again")
        assert (e1.seq, e2.seq, e3.seq) == (1, 2, 3)
        assert (tmp_path / "audit.jsonl").exists()

    def test_durable_before_return(self, tmp_path):
        from ai_kos.audit import AuditLog
        log = AuditLog(tmp_path / "audit.jsonl")
        log.log("s", "durable")
        lines = [l for l in (tmp_path / "audit.jsonl").read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["preview"] == "durable"

    def test_preview_cap(self, tmp_path):
        from ai_kos.audit import AuditLog
        log = AuditLog(tmp_path / "audit.jsonl")
        e = log.log("s", "x" * 1000, preview_chars=100)
        assert len(e.preview) == 100
        assert e.preview == "x" * 100

    def test_read_filters(self, tmp_path):
        from ai_kos.audit import AuditLog
        log = AuditLog(tmp_path / "audit.jsonl")
        log.log("src-a", "one", kind="model_input")
        log.log("src-a", "two", kind="tool_output")
        log.log("src-b", "three", kind="model_input")
        assert len(log.read(source="src-a")) == 2
        assert len(log.read(kind="model_input")) == 2
        assert len(log.read(source="src-b", kind="model_input")) == 1
        assert len(log.read(since_seq=1)) == 2

    def test_tail(self, tmp_path):
        from ai_kos.audit import AuditLog
        log = AuditLog(tmp_path / "audit.jsonl")
        assert log.tail() is None
        log.log("s", "one")
        log.log("s", "two")
        assert log.tail().seq == 2

    def test_torn_tail_repair(self, tmp_path):
        from ai_kos.audit import AuditLog
        p = tmp_path / "audit.jsonl"
        p.write_text(json.dumps(_entry(seq=1)) + "\n" +
                     '{"seq": 2, "at": "x", "source": "s", "kind": "k", "preview": "p", "met')
        log = AuditLog(p)
        log.repair_tail()
        entries = log.read()
        assert len(entries) == 1
        assert entries[0].seq == 1

    def test_mid_log_corruption_raises(self, tmp_path):
        from ai_kos.audit import AuditLog, AuditError
        p = tmp_path / "audit.jsonl"
        p.write_text(json.dumps(_entry(seq=1)) + "\nNOT JSON\n" +
                     json.dumps(_entry(seq=2)) + "\n")
        with pytest.raises(AuditError):
            AuditLog(p)  # committed mid-log corruption is detected on open


class TestDefaultPath:
    def test_default_audit_path(self, monkeypatch, tmp_path):
        from ai_kos import config
        kd = str(tmp_path / "knowledge")
        monkeypatch.setattr(config, "_config", {"paths": {"knowledge_dir": kd}})
        from ai_kos.audit import default_audit_path
        assert default_audit_path() == (tmp_path / "knowledge" / "audit" / "audit.jsonl")


class TestWorkerIntegration:
    def test_worker_logs_objective(self, tmp_path, monkeypatch):
        """atq_worker.run() logs the objective via the audit hook."""
        from ai_kos.audit import AuditLog
        from ai_kos.atq_worker import Worker

        audit_path = tmp_path / "audit" / "audit.jsonl"
        monkeypatch.setattr("ai_kos.audit.default_audit_path", lambda: audit_path)

        w = Worker("t_abc123", board="test-board", workdir=tmp_path)
        w.claimed = True

        def fake_run(cmd, timeout=120):
            return {"exit_code": 0, "stdout": "", "stderr": ""}

        with patch("ai_kos.atq_worker._run", side_effect=fake_run):
            with patch.object(w, "comment", return_value=""):
                with patch.object(w, "complete", return_value=""):
                    rc = w.run(cmd="echo hi")

        assert rc == 0
        entries = AuditLog(audit_path).read()
        hits = [e for e in entries if e.source == "atq-worker"]
        assert hits, "audit hook should log an atq-worker entry"
        assert hits[0].meta.get("task_id") == "t_abc123"
        assert hits[0].meta.get("lane") == "shell"
