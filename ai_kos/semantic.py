"""AI-KOS SemanticSearch — vector embeddings for semantic article search.

Adopts Cloudflare AI Search / Vectorize patterns:
- Optional sentence-transformers for 384-dim embeddings
- FAISS flat index for cosine similarity search
- Hybrid RRF (Reciprocal Rank Fusion) combining TF-IDF + vector scores
- Graceful fallback to keyword-only when dependencies are missing

Dependencies (optional):
    sentence-transformers  — pip install sentence-transformers
    faiss-cpu              — pip install faiss-cpu

If either is missing, semantic search degrades gracefully to keyword-only.
"""

import logging
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ai-kos.semantic")

# ── Optional dependency detection ───────────────────────────────────────────

_sentence_transformers_available = False
_faiss_available = False
_numpy_available = False

try:
    import numpy as np
    _numpy_available = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    _sentence_transformers_available = True
except ImportError:
    pass

try:
    import faiss
    _faiss_available = True
except ImportError:
    pass

SEMANTIC_AVAILABLE = _sentence_transformers_available and _faiss_available and _numpy_available

# ── Constants ────────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
RRF_K = 60  # RRF constant — higher = more weight on lower-ranked items
DEFAULT_SEMANTIC_THRESHOLD = 0.7  # cosine similarity threshold for auto-linking

_VECTORS_DIR_NAME = ".vectors"


# ── Embedding Model ──────────────────────────────────────────────────────────

class EmbeddingModel:
    """Wraps sentence-transformers model with caching and lazy loading."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            if not _sentence_transformers_available:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: List[str]) -> "np.ndarray":
        """Encode texts to 384-dim embeddings. Returns numpy array."""
        if not texts:
            return np.array([]).reshape(0, EMBEDDING_DIM) if _numpy_available else []
        return self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    def encode_single(self, text: str) -> "np.ndarray":
        """Encode a single text."""
        return self.encode([text])[0]


# ── FAISS Index ──────────────────────────────────────────────────────────────

class VectorIndex:
    """FAISS flat index for cosine similarity search over article embeddings.

    Index is persisted to knowledge/.vectors/index.faiss + slugs.json.
    """

    def __init__(self, vectors_dir: Optional[str] = None):
        self._dir = Path(vectors_dir) if vectors_dir else self._default_dir()
        self._index: Optional["faiss.Index"] = None
        self._slugs: List[str] = []  # slug at each index position
        self._loaded = False

    def _default_dir(self) -> Path:
        from ai_kos.config import get
        knowledge_dir = get("paths", "knowledge_dir", default="knowledge")
        return Path(knowledge_dir) / _VECTORS_DIR_NAME

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._index is not None

    def _index_path(self) -> Path:
        return self._dir / "index.faiss"

    def _slugs_path(self) -> Path:
        return self._dir / "slugs.json"

    def _ensure_deps(self):
        if not _faiss_available:
            raise RuntimeError("faiss-cpu not installed. Install with: pip install faiss-cpu")
        if not _numpy_available:
            raise RuntimeError("numpy not installed")

    def build(self, articles: List[dict], embedding_model: EmbeddingModel, force: bool = False) -> int:
        """Build FAISS index from article embeddings.

        Args:
            articles: List of dicts with 'slug', 'title', 'summary', 'body' (or 'raw' markdown)
            embedding_model: EmbeddingModel instance
            force: If True, rebuild even if index exists

        Returns:
            Number of articles indexed
        """
        if not force and self._index_exists():
            self.load()
            if self._loaded:
                return len(self._slugs)

        self._ensure_deps()

        slugs = []
        texts = []
        for art in articles:
            slug = art.get("slug", "")
            if not slug:
                continue
            # Combine text fields for embedding
            text = f"{art.get('title', '')} {art.get('summary', '')} {art.get('body', '')}"
            if not text.strip():
                continue
            slugs.append(slug)
            texts.append(text)

        if not texts:
            logger.warning("VectorIndex: no articles to index")
            self._index = None
            self._slugs = []
            return 0

        embeddings = embedding_model.encode(texts)
        dim = embeddings.shape[1]

        # Create FAISS index for inner product (cosine similarity on normalized vectors)
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))

        self._index = index
        self._slugs = slugs
        self._loaded = True
        self._save()

        logger.info(f"VectorIndex built: {len(slugs)} articles, dim={dim}")
        return len(slugs)

    def search(self, query_embedding: "np.ndarray", top_k: int = 20) -> List[Tuple[str, float]]:
        """Search for similar articles by cosine similarity.

        Returns list of (slug, similarity_score) tuples.
        """
        if not self.is_loaded:
            return []

        query = np.array([query_embedding]).astype(np.float32)
        scores, indices = self._index.search(query, min(top_k, len(self._slugs)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._slugs):
                continue
            # FAISS IndexFlatIP returns inner product; normalized vectors give cosine similarity
            similarity = float(score)
            if similarity > 0:
                results.append((self._slugs[idx], similarity))

        return results

    def get_similar_to_slug(self, slug: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """Find articles similar to a given slug (excluding itself)."""
        if slug not in self._slugs:
            return []

        idx = self._slugs.index(slug)
        vector = self._index.reconstruct(idx)
        results = self.search(vector, top_k=top_k + 1)
        # Filter out self
        return [(s, score) for s, score in results if s != slug][:top_k]

    def _index_exists(self) -> bool:
        return self._index_path().exists() and self._slugs_path().exists()

    def _save(self):
        """Persist index and slug mapping to disk."""
        if self._index is None:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path()))

        import json
        self._slugs_path().write_text(json.dumps(self._slugs))

    def load(self) -> bool:
        """Load index from disk. Returns True if successful."""
        if not self._index_exists():
            return False

        try:
            self._ensure_deps()
            self._index = faiss.read_index(str(self._index_path()))

            import json
            self._slugs = json.loads(self._slugs_path().read_text())
            self._loaded = True
            logger.info(f"VectorIndex loaded: {len(self._slugs)} vectors")
            return True
        except Exception as e:
            logger.warning(f"VectorIndex load failed: {e}")
            self._index = None
            self._slugs = []
            return False

    def delete(self):
        """Remove persisted index files."""
        for p in [self._index_path(), self._slugs_path()]:
            if p.exists():
                p.unlink()


# ── Hybrid Search ────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    tfidf_rankings: Dict[str, int],
    vector_rankings: Dict[str, int],
    k: int = RRF_K,
) -> Dict[str, float]:
    """Combine two ranked lists using Reciprocal Rank Fusion.

    RRF(score) = sum(1 / (k + rank_i)) for each list i.

    Args:
        tfidf_rankings: {slug: rank} from TF-IDF search (1-indexed)
        vector_rankings: {slug: rank} from vector search (1-indexed)
        k: RRF constant (default 60)

    Returns:
        {slug: fused_score} sorted from high to low
    """
    scores: Dict[str, float] = {}

    for slug, rank in tfidf_rankings.items():
        scores[slug] = 1.0 / (k + rank)

    for slug, rank in vector_rankings.items():
        scores[slug] = scores.get(slug, 0.0) + 1.0 / (k + rank)

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


class HybridSearcher:
    """Combines TF-IDF keyword search with vector semantic search via RRF.

    Usage:
        searcher = HybridSearcher()
        results = searcher.search("What is a knowledge graph?")
        # Falls back to keyword-only if embeddings unavailable
    """

    def __init__(self, vector_index: Optional[VectorIndex] = None, embedding_model: Optional[EmbeddingModel] = None):
        self.vector_index = vector_index or VectorIndex()
        self.embedding_model = embedding_model or EmbeddingModel()
        self._semantic_ready = SEMANTIC_AVAILABLE

    def search(
        self,
        query: str,
        top_k: int = 10,
        article_type: Optional[str] = None,
        min_semantic_threshold: float = 0.0,
    ) -> List[dict]:
        """Hybrid search: RRF fusion of TF-IDF + vector results.

        Args:
            query: Search query
            top_k: Max results
            article_type: Optional type filter
            min_semantic_threshold: Minimum cosine similarity for vector hits

        Returns:
            List of result dicts with 'slug', 'title', 'score', 'tfidf_rank', 'semantic_rank'
        """
        from ai_kos.search import search as tfidf_search, get_index

        # 1. Get TF-IDF results
        tfidf_results = tfidf_search(query, top_k=top_k * 2, article_type=article_type)
        tfidf_rankings = {r["slug"]: i + 1 for i, r in enumerate(tfidf_results)}

        # 2. Get vector results (if available)
        vector_rankings: Dict[str, int] = {}
        semantic_results: Dict[str, dict] = {}
        if self._semantic_ready and self.vector_index.is_loaded:
            try:
                q_embedding = self.embedding_model.encode_single(query)
                vec_hits = self.vector_index.search(q_embedding, top_k=top_k * 2)
                for rank, (slug, score) in enumerate(vec_hits, 1):
                    if score >= min_semantic_threshold:
                        vector_rankings[slug] = rank
                        semantic_results[slug] = {"semantic_score": round(score, 4)}
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to keyword: {e}")
                self._semantic_ready = False

        # 3. RRF fusion
        if vector_rankings:
            fused = reciprocal_rank_fusion(tfidf_rankings, vector_rankings)
        else:
            # Keyword-only: use TF-IDF rankings directly
            fused = {slug: 1.0 / (RRF_K + rank) for slug, rank in tfidf_rankings.items()}

        # 4. Build results
        index = get_index()
        results = []
        for slug, score in list(fused.items())[:top_k]:
            if slug not in index.docs:
                continue
            doc = index.docs[slug]
            entry = {
                "slug": slug,
                "title": doc.title,
                "type": doc.article_type,
                "score": round(score, 6),
                "tfidf_rank": tfidf_rankings.get(slug),
                "semantic_rank": vector_rankings.get(slug),
                "keywords": doc.keywords,
                "summary": doc.summary,
            }
            if slug in semantic_results:
                entry["semantic_score"] = semantic_results[slug]["semantic_score"]
            results.append(entry)

        return results

    def ensure_index(self, knowledge_dir: str = "knowledge") -> bool:
        """Ensure the vector index is built (or loaded from disk).

        Returns True if semantic search is ready.
        """
        if not self._semantic_ready:
            return False

        if self.vector_index.is_loaded:
            return True

        # Try loading from disk first
        if self.vector_index.load():
            return True

        # Build from scratch
        from ai_kos.articles import list_articles, read_article

        articles = []
        for art in list_articles():
            full = read_article(art["slug"])
            body = full["body"] if full else art.get("summary", "")
            articles.append({
                "slug": art["slug"],
                "title": art["title"],
                "summary": art.get("summary", ""),
                "body": body,
            })

        if articles:
            try:
                self.vector_index.build(articles, self.embedding_model, force=True)
                return True
            except Exception as e:
                logger.warning(f"Vector index build failed: {e}")
                self._semantic_ready = False

        return False


# ── Module-level singleton ───────────────────────────────────────────────────

_hybrid_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher


def hybrid_search(query: str, top_k: int = 10, article_type: Optional[str] = None) -> List[dict]:
    """Hybrid semantic + keyword search. Falls back gracefully to keyword-only."""
    return get_hybrid_searcher().search(query, top_k, article_type)


def ensure_semantic_index() -> bool:
    """Build or load the semantic index. Call once at startup."""
    return get_hybrid_searcher().ensure_index()


def semantic_available() -> bool:
    """Check if semantic search dependencies are installed."""
    return SEMANTIC_AVAILABLE
