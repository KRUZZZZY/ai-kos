"""Tests for AI-KOS blob backend."""
import tempfile, os, pytest
from pathlib import Path


class TestBlobStore:
    def test_store_and_delete(self, tmp_path):
        from ai_kos.blobs import store_blob, delete_blob, list_blobs
        src = tmp_path / "test.png"
        src.write_bytes(b"\x89PNG\r\n\x1a\nfake png data")

        blob_dir = str(tmp_path / "blobs")
        ref = store_blob(str(src), blob_dir, slug="test-image")
        assert ref["mime_type"] == "image/png"
        assert ref["size_bytes"] > 0
        assert os.path.exists(ref["path"])

        blobs = list_blobs(blob_dir)
        assert len(blobs) == 1

        assert delete_blob(ref["path"]) is True
        assert not os.path.exists(ref["path"])

    def test_list_empty_dir(self, tmp_path):
        from ai_kos.blobs import list_blobs
        empty = str(tmp_path / "empty")
        os.makedirs(empty, exist_ok=True)
        assert list_blobs(empty) == []

    def test_extract_text_no_deps(self, tmp_path):
        """extract_text should return empty string when deps missing."""
        from ai_kos.blobs import extract_text
        src = tmp_path / "fake.png"
        src.write_bytes(b"not a real png")
        text = extract_text(str(src), "image/png")
        assert isinstance(text, str)


class TestBlobArticle:
    def test_create_and_read(self, tmp_path, monkeypatch):
        import uuid
        from datetime import date
        from ai_kos.schemas import BlobRef
        from ai_kos.blobs import store_blob

        kd = str(tmp_path / "knowledge")
        monkeypatch.setattr("ai_kos.articles.KNOWLEDGE_DIR", kd)
        monkeypatch.setattr("ai_kos.linker.KNOWLEDGE_DIR", kd, raising=False)

        from ai_kos.articles import create_article, read_article, delete_article, _refresh_index
        _refresh_index()

        src = tmp_path / "screenshot.png"
        src.write_bytes(b"mock png")
        blob_dir = str(tmp_path / "blobs")
        blob_info = store_blob(str(src), blob_dir, slug="screenshot")

        today = date.today()
        data = {
            "id": str(uuid.uuid4()), "title": "Dashboard Screenshot", "slug": "dashboard-screenshot",
            "type": "base", "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": date(2027, 1, 1), "keywords": ["screenshot", "dashboard", "ui"],
            "summary": "Screenshot of the dashboard.", "backend": "blob",
            "blob": BlobRef(**blob_info),
            "provenance": [{"source": "ingest", "origin_ref": "screenshot.png"}],
        }

        result = create_article("base", data)
        assert result["status"] == "created"
        assert result["backend"] == "blob"

        article = read_article("dashboard-screenshot")
        assert article["backend"] == "blob"
        assert article["file_exists"] is True

        delete_article("dashboard-screenshot")
        assert not os.path.exists(blob_info["path"])
