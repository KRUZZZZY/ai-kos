"""Tests for AI-KOS SemanticSearch — vector embeddings, FAISS, hybrid RRF search."""

import math
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_kos.semantic import (
    SEMANTIC_AVAILABLE,
    EMBEDDING_DIM,
    RRF_K,
    EmbeddingModel,
    VectorIndex,
    HybridSearcher,
    reciprocal_rank_fusion,
    semantic_available,
    ensure_semantic_index,
    hybrid_search,
)


class TestReciprocalRankFusion:
    def test_basic_fusion(self):
        tfidf = {"a": 1, "b": 2}
        vec = {"b": 1, "c": 2}
        fused = reciprocal_rank_fusion(tfidf, vec, k=60)

        # b appears in both lists (rank 2 in tfidf, rank 1 in vec) → highest
        assert fused["b"] > fused.get("a", 0)
        assert fused["b"] > fused.get("c", 0)

    def test_single_list(self):
        tfidf = {"a": 1, "b": 2, "c": 3}
        fused = reciprocal_rank_fusion(tfidf, {}, k=60)
        assert fused["a"] > fused["b"] > fused["c"]

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion({}, {}, k=60)
        assert fused == {}

    def test_k_small_gives_less_equalizing(self):
        tfidf = {"a": 1}
        vec = {"a": 1}
        k_small = reciprocal_rank_fusion(tfidf, vec, k=1)
        k_large = reciprocal_rank_fusion(tfidf, vec, k=60)
        # With smaller k, the single rank-1 hit gets more relative weight
        assert k_small["a"] > k_large["a"]

    def test_rrf_formula(self):
        tfidf = {"x": 2}
        vec = {"x": 3}
        fused = reciprocal_rank_fusion(tfidf, vec, k=60)
        expected = 1.0 / (60 + 2) + 1.0 / (60 + 3)
        assert math.isclose(fused["x"], expected, rel_tol=1e-9)


class TestEmbeddingModel:
    def test_not_available_without_deps(self):
        if SEMANTIC_AVAILABLE:
            pytest.skip("Dependencies are installed — cannot test unavailable path")
        model = EmbeddingModel()
        with pytest.raises(RuntimeError, match="not installed"):
            _ = model.model

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not installed")
    def test_encode_single(self):
        model = EmbeddingModel()
        vec = model.encode_single("test sentence")
        assert len(vec) == EMBEDDING_DIM

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not installed")
    def test_encode_batch(self):
        model = EmbeddingModel()
        import numpy as np
        vecs = model.encode(["one", "two", "three"])
        assert vecs.shape == (3, EMBEDDING_DIM)

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not installed")
    def test_embeddings_are_normalized(self):
        model = EmbeddingModel()
        import numpy as np
        vec = model.encode_single("unit test vector")
        norm = np.linalg.norm(vec)
        assert math.isclose(norm, 1.0, rel_tol=1e-5)

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not installed")
    def test_similar_sentences_higher_similarity(self):
        model = EmbeddingModel()
        import numpy as np
        v1 = model.encode_single("cloud computing at the edge")
        v2 = model.encode_single("serverless functions at the edge")
        v3 = model.encode_single("baking a chocolate cake")
        sim_12 = np.dot(v1, v2)
        sim_13 = np.dot(v1, v3)
        assert sim_12 > sim_13  # similar topics = higher cosine similarity


class TestVectorIndex:
    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="faiss not installed")
    def test_build_and_search(self, tmp_path):
        model = EmbeddingModel()
        vi = VectorIndex(vectors_dir=str(tmp_path))

        articles = [
            {"slug": "a", "title": "Cloudflare Workers", "summary": "Serverless at the edge", "body": "V8 isolates"},
            {"slug": "b", "title": "AWS Lambda", "summary": "Serverless functions", "body": "Containers"},
            {"slug": "c", "title": "Baking bread", "summary": "How to bake", "body": "Flour and water"},
        ]

        count = vi.build(articles, model, force=True)
        assert count == 3
        assert vi.is_loaded

        results = vi.search(model.encode_single("edge computing serverless"), top_k=2)
        assert len(results) == 2
        # "Cloudflare Workers" should be top result
        assert results[0][0] == "a"
        assert results[0][1] > 0.0

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="faiss not installed")
    def test_similar_to_slug(self, tmp_path):
        model = EmbeddingModel()
        vi = VectorIndex(vectors_dir=str(tmp_path))

        articles = [
            {"slug": "a", "title": "Graph theory", "summary": "Nodes and edges", "body": ""},
            {"slug": "b", "title": "Network theory", "summary": "Network science", "body": ""},
            {"slug": "c", "title": "Cooking pasta", "summary": "Italian food", "body": ""},
        ]

        vi.build(articles, model, force=True)
        similar = vi.get_similar_to_slug("a", top_k=2)
        assert similar[0][0] == "b"  # "Network theory" closest to "Graph theory"
        assert similar[0][1] > 0.0

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="faiss not installed")
    def test_persist_and_load(self, tmp_path):
        model = EmbeddingModel()
        vi = VectorIndex(vectors_dir=str(tmp_path))

        articles = [{"slug": "x", "title": "Test", "summary": "Test article", "body": "Content"}]
        vi.build(articles, model, force=True)

        # Verify files exist
        assert (tmp_path / "index.faiss").exists()
        assert (tmp_path / "slugs.json").exists()

        # Load into a new instance
        vi2 = VectorIndex(vectors_dir=str(tmp_path))
        assert vi2.load()
        assert vi2.is_loaded
        assert len(vi2._slugs) == 1
        assert vi2._slugs[0] == "x"

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="faiss not installed")
    def test_search_empty_index(self, tmp_path):
        model = EmbeddingModel()
        vi = VectorIndex(vectors_dir=str(tmp_path))
        # Don't build — just try searching
        results = vi.search(model.encode_single("query"))
        assert results == []

    @pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="faiss not installed")
    def test_delete_index(self, tmp_path):
        model = EmbeddingModel()
        vi = VectorIndex(vectors_dir=str(tmp_path))
        articles = [{"slug": "d", "title": "Delete me", "summary": "x", "body": "x"}]
        vi.build(articles, model, force=True)
        vi.delete()
        assert not (tmp_path / "index.faiss").exists()


class TestHybridSearcher:
    def test_falls_back_when_deps_missing(self):
        if SEMANTIC_AVAILABLE:
            pytest.skip("Dependencies installed — cannot test fallback")
        searcher = HybridSearcher()
        assert not searcher._semantic_ready
        ready = searcher.ensure_index()
        assert not ready

    def test_reciprocal_rank_fusion_integration(self):
        """Verify RRF correctly combines two ranking signals."""
        tfidf = {"slug_a": 1, "slug_b": 2, "slug_c": 3}
        vec = {"slug_b": 1, "slug_c": 3, "slug_d": 2}
        fused = reciprocal_rank_fusion(tfidf, vec, k=60)

        # slug_b ranks high in both → should be #1
        keys_by_score = sorted(fused, key=fused.get, reverse=True)
        assert keys_by_score[0] == "slug_b"


class TestSemanticAvailable:
    def test_returns_bool(self):
        result = semantic_available()
        assert isinstance(result, bool)
