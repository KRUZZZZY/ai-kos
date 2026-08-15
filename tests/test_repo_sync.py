"""Tests for ai_kos.repo_sync — commit/push/verify flow + help-guides subset."""

import json
from pathlib import Path

import pytest

from ai_kos.repo_sync import (
    RepoSyncError,
    build_help_guides_subset,
    repo_sync,
    sync_help_guides,
    sync_repo,
)


class _FakeRun:
    """Records commands; canned stdout for status/head/remote calls."""

    def __init__(self):
        self.calls = []

    def __call__(self, args, cwd=None, dry_run=False, timeout=300):
        self.calls.append({"args": list(args), "cwd": str(cwd) if cwd else None,
                           "dry_run": dry_run})
        cmd = args[0]
        if cmd == "git" and "status" in args:
            return {"returncode": 0, "stdout": " M file.md\n?? new.md\n", "stderr": ""}
        if cmd == "git" and args[1] == "rev-parse":
            return {"returncode": 0, "stdout": "abc1234", "stderr": ""}
        if cmd == "git" and args[1] == "remote":
            return {"returncode": 0, "stdout": "https://github.com/x/y.git", "stderr": ""}
        if cmd == "git" and args[1] == "ls-remote":
            return {"returncode": 0, "stdout": "abc1234\trefs/heads/master", "stderr": ""}
        if cmd == "git" and args[1] == "clone":
            return {"returncode": 0, "stdout": "cloned", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}


def _fake_repo(tmp_path, name="repo"):
    d = tmp_path / name
    (d / ".git").mkdir(parents=True)
    return d


def _mk_article(d, slug, atype, summary="A summary of the guide."):
    p = d / f"{slug}.md"
    p.write_text(f"---\ntitle: {slug}\ntype: {atype}\nslug: {slug}\n"
                 f"summary: '{summary}'\n---\n\nBody of {slug}.\n")
    return p


class TestSyncRepo:
    def test_skips_non_git_dir(self, tmp_path, monkeypatch):
        plain = tmp_path / "nope"
        plain.mkdir()
        out = sync_repo(plain, "msg")
        assert out["status"] == "skipped"

    def test_clean_repo_skips(self, tmp_path, monkeypatch):
        fake = _FakeRun()
        fake.calls = []
        orig = None
        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", fake)

        def clean(args, cwd=None, dry_run=False, timeout=300):
            fake.calls.append({"args": list(args), "cwd": str(cwd), "dry_run": dry_run})
            if "status" in args:
                return {"returncode": 0, "stdout": "", "stderr": ""}
            return {"returncode": 0, "stdout": "", "stderr": ""}

        monkeypatch.setattr(rs, "_run", clean)
        out = sync_repo(_fake_repo(tmp_path), "msg")
        assert out["status"] == "clean"
        # only status was called — no add/commit/push
        assert all("add" not in c["args"] and "commit" not in c["args"] and "push" not in c["args"]
                   for c in fake.calls)

    def test_dirty_repo_full_sequence(self, tmp_path, monkeypatch):
        fake = _FakeRun()
        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", fake)
        out = sync_repo(_fake_repo(tmp_path), "chore: sync")
        cmds = [c["args"] for c in fake.calls]
        assert ["git", "add", "-A"] in cmds
        assert ["git", "commit", "-m", "chore: sync"] in cmds
        assert ["git", "push"] in cmds
        assert out["status"] == "pushed"
        assert out["changed"] == 2

    def test_dry_run_never_commits(self, tmp_path, monkeypatch):
        fake = _FakeRun()
        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", fake)
        sync_repo(_fake_repo(tmp_path), "msg", dry_run=True)
        # mutating commands are faked (dry_run=True); read-only status is real
        mutating = [c for c in fake.calls
                    if any(k in c["args"] for k in ("add", "commit", "push"))]
        assert mutating and all(c["dry_run"] for c in mutating)

    def test_verify_mismatch_raises(self, tmp_path, monkeypatch):
        def mismatched(args, cwd=None, dry_run=False, timeout=300):
            if args[1] == "ls-remote":
                return {"returncode": 0, "stdout": "deadbee\trefs/heads/master", "stderr": ""}
            return _FakeRun().__call__(args, cwd, dry_run, timeout)

        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", mismatched)
        with pytest.raises(RepoSyncError):
            sync_repo(_fake_repo(tmp_path), "msg")


class TestHelpGuidesSubset:
    def test_builds_subset_and_readme(self, tmp_path):
        kb = tmp_path / "knowledge" / "bundles" / "general"
        kb.mkdir(parents=True)
        _mk_article(kb, "guide-a", "help")
        _mk_article(kb, "proc-b", "process")
        _mk_article(kb, "base-c", "base")  # excluded
        staging = tmp_path / "guides"
        res = build_help_guides_subset(tmp_path / "knowledge", staging)
        assert res == {"help": 1, "process": 1}
        assert (staging / "guide-a.md").exists()
        assert (staging / "proc-b.md").exists()
        assert not (staging / "base-c.md").exists()
        readme = (staging / "README.md").read_text()
        assert "guide-a" in readme and "proc-b" in readme and "base-c" not in readme

    def test_collision_raises(self, tmp_path):
        kb = tmp_path / "knowledge" / "bundles" / "general"
        kb.mkdir(parents=True)
        _mk_article(kb, "dup", "help")
        # same frontmatter slug, different filename → slug collision across types
        (kb / "dup-copy.md").write_text(
            "---\ntitle: dup\ntype: process\nslug: dup\nsummary: 'x'\n---\n\nBody.\n")
        with pytest.raises(RepoSyncError):
            build_help_guides_subset(tmp_path / "knowledge", tmp_path / "guides")


class TestRepoSync:
    def test_master_flow_code_and_knowledge(self, tmp_path, monkeypatch):
        code = _fake_repo(tmp_path, "code")
        (code / "knowledge" / ".git").mkdir(parents=True)
        fake = _FakeRun()
        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", fake)
        out = repo_sync(code_dir=str(code))
        assert len(out["results"]) == 2
        assert all(r["status"] == "pushed" for r in out["results"])

    def test_help_guides_clones_if_missing(self, tmp_path, monkeypatch):
        code = _fake_repo(tmp_path, "code")
        (code / "knowledge" / "bundles" / "general").mkdir(parents=True)
        _mk_article(code / "knowledge" / "bundles" / "general", "guide", "help")
        fake = _FakeRun()
        import ai_kos.repo_sync as rs
        monkeypatch.setattr(rs, "_run", fake)
        monkeypatch.setattr(rs, "HELP_GUIDES_DIR_DEFAULT",
                            tmp_path / "help-guides")
        out = repo_sync(code_dir=str(code), include_help_guides=True)
        # clone called for missing guides repo
        assert any(c["args"][1] == "clone" for c in fake.calls)
        assert any("guides" in r["repo"] for r in out["results"])
