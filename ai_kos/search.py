"""AI-KOS search engine — TF-IDF full-text search + similarity comparison.

Scales to thousands of articles. Pure Python, no extra deps.
Features:
  - Full-text search with TF-IDF scoring and snippet extraction
  - Compare: find N most similar articles to a given slug
  - Hybrid mode: combine text relevance with keyword match bonus
  - Cached index with automatic rebuild on article changes
"""

import re
import math
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("ai-kos.search")

# ── Tokenizer ──────────────────────────────────────────────────

_STOP_WORDS = {
    'the','a','an','is','are','was','were','be','been','being','have','has','had',
    'do','does','did','will','would','shall','should','can','could','may','might',
    'i','me','my','we','our','you','your','he','she','it','its','they','them',
    'this','that','these','those','in','on','at','to','for','of','with','by',
    'from','up','about','into','through','during','before','after','above','below',
    'between','and','but','or','not','no','nor','so','if','then','else','when',
    'where','why','how','all','each','every','both','few','more','most','other',
    'some','such','only','own','same','too','very','just','also','now','here','there',
}

def tokenize(text: str) -> List[str]:
    """Lowercase, split on word boundaries, remove stop words and short tokens."""
    tokens = re.findall(r'[a-z0-9]{2,}', text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


# ── TF-IDF Index ───────────────────────────────────────────────

@dataclass
class DocInfo:
    slug: str
    title: str
    article_type: str
    keywords: List[str]
    summary: str
    filepath: str
    mtime: float           # for cache invalidation
    tokens: List[str] = field(default_factory=list)
    term_freqs: Dict[str, int] = field(default_factory=dict)  # term → count


class SearchIndex:
    """In-memory TF-IDF index over all knowledge articles."""

    def __init__(self):
        self.docs: Dict[str, DocInfo] = {}      # slug → DocInfo
        self.inverted: Dict[str, List[str]] = defaultdict(list)  # term → [slugs]
        self.doc_freqs: Dict[str, int] = {}      # term → document frequency
        self._total_docs = 0

    def clear(self):
        self.docs.clear()
        self.inverted.clear()
        self.doc_freqs.clear()
        self._total_docs = 0

    def _read_doc(self, filepath: str) -> Optional[DocInfo]:
        """Parse a markdown file into a DocInfo."""
        import yaml
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                return None
            parts = content.split('---', 2)
            fm = yaml.safe_load(parts[1]) or {}
            slug = fm.get('slug', Path(filepath).stem)
            # Combine all text fields for indexing
            body = parts[2] if len(parts) > 2 else ""
            text = f"{fm.get('title','')} {fm.get('summary','')} {' '.join(fm.get('keywords',[]))} {body}"
            tokens = tokenize(text)
            tfs = {}
            for t in tokens:
                tfs[t] = tfs.get(t, 0) + 1
            return DocInfo(
                slug=slug,
                title=fm.get('title', slug),
                article_type=fm.get('type', 'base'),
                keywords=fm.get('keywords', []),
                summary=fm.get('summary', ''),
                filepath=filepath,
                mtime=Path(filepath).stat().st_mtime,
                tokens=tokens,
                term_freqs=tfs,
            )
        except Exception as e:
            logger.warning(f"Index: skip {filepath}: {e}")
            return None

    def build(self, knowledge_dir: str = "knowledge", force: bool = False) -> int:
        """Build or update the index. Returns number of docs indexed."""
        # Check cache: only re-read files with changed mtime
        if not force and self.docs:
            changed = 0
            current_slugs = set()
            for md in Path(knowledge_dir).rglob("*.md"):
                slug = md.stem
                current_slugs.add(slug)
                mtime = md.stat().st_mtime
                if slug not in self.docs or self.docs[slug].mtime != mtime:
                    doc = self._read_doc(str(md))
                    if doc:
                        self._remove_doc(slug)
                        self._add_doc(doc)
                        changed += 1
            # Remove deleted articles
            for slug in list(self.docs):
                if slug not in current_slugs:
                    self._remove_doc(slug)
                    changed += 1
            if changed:
                logger.info(f"Index updated: {changed} docs changed")
            return len(self.docs)

        # Full rebuild
        self.clear()
        for md in Path(knowledge_dir).rglob("*.md"):
            doc = self._read_doc(str(md))
            if doc:
                self._add_doc(doc)
        logger.info(f"Index built: {self._total_docs} documents, {len(self.doc_freqs)} unique terms")
        return self._total_docs

    def _add_doc(self, doc: DocInfo):
        self.docs[doc.slug] = doc
        self._total_docs = len(self.docs)
        for term in doc.term_freqs:
            self.inverted[term].append(doc.slug)
        # Recompute doc frequencies
        self.doc_freqs = {t: len(slugs) for t, slugs in self.inverted.items()}

    def _remove_doc(self, slug: str):
        if slug not in self.docs:
            return
        for term in self.docs[slug].term_freqs:
            if term in self.inverted:
                self.inverted[term] = [s for s in self.inverted[term] if s != slug]
                if not self.inverted[term]:
                    del self.inverted[term]
        del self.docs[slug]
        self._total_docs = len(self.docs)

    def _idf(self, term: str) -> float:
        """Inverse document frequency."""
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        return math.log((self._total_docs + 1) / (df + 1)) + 1.0

    def _tfidf_vector(self, doc: DocInfo) -> Dict[str, float]:
        """Sparse TF-IDF vector for a document."""
        vec = {}
        max_tf = max(doc.term_freqs.values()) if doc.term_freqs else 1
        for term, tf in doc.term_freqs.items():
            idf = self._idf(term)
            vec[term] = (tf / max_tf) * idf  # normalized TF * IDF
        return vec

    def search(self, query: str, top_k: int = 10, article_type: Optional[str] = None) -> List[dict]:
        """Full-text search with TF-IDF scoring + keyword match bonus. Returns ranked results with snippets."""
        if not self.docs:
            self.build()

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Compute query TF-IDF vector
        q_tf = {}
        for t in query_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        max_q_tf = max(q_tf.values())
        q_vec = {}
        for t, tf in q_tf.items():
            q_vec[t] = (tf / max_q_tf) * self._idf(t)

        # Score every document
        scores: Dict[str, float] = {}
        for slug, doc in self.docs.items():
            if article_type and doc.article_type != article_type:
                continue

            # TF-IDF cosine similarity
            dot = 0.0
            for term, q_weight in q_vec.items():
                if term in doc.term_freqs:
                    doc_tfidf = (doc.term_freqs[term] / max(doc.term_freqs.values())) * self._idf(term)
                    dot += q_weight * doc_tfidf
            if dot > 0:
                # Keyword match bonus: +30% per matching keyword
                kw_match = sum(1 for kw in doc.keywords if any(qt in kw.lower() for qt in query_tokens))
                bonus = 1.0 + kw_match * 0.3
                scores[slug] = dot * bonus

        # Sort and take top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Build results with snippets
        results = []
        for slug, score in ranked:
            doc = self.docs[slug]
            snippet = self._extract_snippet(doc, query_tokens)
            results.append({
                "slug": slug,
                "title": doc.title,
                "type": doc.article_type,
                "score": round(score, 4),
                "keywords": doc.keywords,
                "summary": doc.summary,
                "snippet": snippet,
            })
        return results

    def compare(self, slug: str, top_k: int = 10) -> List[dict]:
        """Find the N most similar articles to the given slug by TF-IDF cosine similarity."""
        if slug not in self.docs:
            return []

        source = self.docs[slug]
        source_vec = self._tfidf_vector(source)
        source_norm = math.sqrt(sum(v * v for v in source_vec.values())) or 1.0

        scores = []
        for other_slug, doc in self.docs.items():
            if other_slug == slug:
                continue
            doc_vec = self._tfidf_vector(doc)
            doc_norm = math.sqrt(sum(v * v for v in doc_vec.values())) or 1.0

            # Cosine similarity
            dot = 0.0
            for term, s_weight in source_vec.items():
                if term in doc_vec:
                    dot += s_weight * doc_vec[term]

            similarity = dot / (source_norm * doc_norm) if source_norm * doc_norm > 0 else 0.0

            # Keyword overlap bonus
            kw_overlap = len(set(source.keywords) & set(doc.keywords))
            combined = similarity * (1.0 + kw_overlap * 0.1)

            if combined > 0:
                scores.append((other_slug, combined, similarity, kw_overlap))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [{
            "slug": s[0],
            "title": self.docs[s[0]].title,
            "type": self.docs[s[0]].article_type,
            "score": round(s[1], 4),
            "text_similarity": round(s[2], 4),
            "shared_keywords": s[3],
            "keywords": self.docs[s[0]].keywords,
        } for s in scores[:top_k]]

    def _extract_snippet(self, doc: DocInfo, query_tokens: List[str], max_len: int = 150) -> str:
        """Extract a relevant snippet from the document body showing query matches."""
        try:
            with open(doc.filepath, 'r') as f:
                content = f.read()
            body = content.split('---', 2)[-1] if content.startswith('---') else content
        except Exception:
            return doc.summary

        sentences = re.split(r'(?<=[.!?])\s+', body)
        if not sentences:
            return doc.summary[:max_len]

        # Score each sentence by number of query token hits
        best_sentence = sentences[0]
        best_score = 0
        for sent in sentences:
            sent_lower = sent.lower()
            score = sum(1 for qt in query_tokens if qt in sent_lower)
            if score > best_score:
                best_score = score
                best_sentence = sent

        snippet = best_sentence.strip()
        if len(snippet) > max_len:
            snippet = snippet[:max_len-3] + '...'
        return snippet if best_score > 0 else doc.summary[:max_len]


# ── Singleton ──────────────────────────────────────────────────

_index: Optional[SearchIndex] = None

def get_index() -> SearchIndex:
    global _index
    if _index is None:
        _index = SearchIndex()
    _index.build()
    return _index

def search(query: str, top_k: int = 10, article_type: Optional[str] = None) -> List[dict]:
    return get_index().search(query, top_k, article_type)

def compare(slug: str, top_k: int = 10) -> List[dict]:
    return get_index().compare(slug, top_k)

def rebuild():
    global _index
    _index = SearchIndex()
    return _index.build(force=True)
