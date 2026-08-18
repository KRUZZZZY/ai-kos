"""AI-KOS linker — automatic typed [[wikilink]] creation between articles sharing >=N keywords.

v1.7: typed relations (see-also edges auto-created), link_count computation,
supersession auto-setting on merge detection, lifecycle management.
v2: "similarity" mode — tier×IDF-weighted keyword vectors (subject_keywords vs
keywords), cosine similarity with a min-evidence gate, per-article link budgets,
mutual top-k edge selection with orphan rescue, and tier-aware merge detection.
Legacy "idf"/"count" modes are preserved byte-for-byte (backward compat §5).

Scans all knowledge articles, finds pairs with keyword overlap, and creates
bidirectional typed [[wikilinks]] in the `related` frontmatter field.
Also handles dedup detection: articles with very high keyword overlap (>80%)
are flagged as merge candidates and their loser gets lifecycle=superseded.
"""

import re, logging, math
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field as dc_field

logger = logging.getLogger("ai-kos.linker")

MERGE_THRESHOLD = 0.80


def _get_default_overlap() -> int:
    try:
        from ai_kos.config import get
        return get("linking", "min_keyword_overlap", default=2)
    except Exception:
        return 2


def _get_linking_mode() -> str:
    """Resolve the active linking mode from config (default 'similarity')."""
    try:
        from ai_kos.config import get
        return get("linking", "mode", default="similarity")
    except Exception:
        return "similarity"


@dataclass
class ArticleMeta:
    slug: str
    filepath: str
    keywords: Set[str]                    # article tier
    related: List[dict]  # v1.7: list of {slug, type} dicts
    title: str = ""
    subject_keywords: Set[str] = dc_field(default_factory=set)   # v2: subject tier
    article_type: str = "base"            # v2
    body_words: int = 0                   # v2: word count minus frontmatter & ## Related (0 for .yaml stubs)
    confidence: float = 0.8               # v2
    retrieval_count: int = 0              # v2
    lifecycle: str = "current"            # v2
    importance: Optional[int] = None      # v2: explicit budget override
    related_pinned: Set[str] = dc_field(default_factory=set)     # v2: human-pinned see-also slugs

    def related_slugs(self) -> Set[str]:
        """Extract bare slugs from related edges."""
        return {r.get("slug", r) if isinstance(r, dict) else r for r in self.related}

    @property
    def all_keywords(self) -> Set[str]:
        """All keywords across tiers: article + subject."""
        return self.keywords | self.subject_keywords


def _read_frontmatter(filepath: str) -> dict:
    """Extension-aware frontmatter load — .yaml stubs are whole-dict files, .md
    use the `---` block (mirrors migrate._load_fm).

    Audit fix 2026-08-18: callers used to do `content.split('---')[1]`
    unconditionally, which IndexErrors on .yaml files and silently disabled
    idempotency checks for them (e.g. the supersede check below).
    """
    import yaml
    with open(filepath) as f:
        content = f.read()
    if filepath.endswith('.yaml'):
        return yaml.safe_load(content) or {}
    parts = content.split('---', 2)
    if len(parts) < 2:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _get_explicit_importance_field() -> str:
    """Frontmatter field carrying the explicit link-budget importance override.

    Audit fix 2026-08-18: `linking.link_budget.importance.explicit_field` was
    dead config (read nowhere) — the field name was hardcoded. It is now the
    single source of truth for the parse-time lookup in `_parse_article`.
    """
    try:
        from ai_kos.config import get
        return get("linking", "link_budget", "importance", "explicit_field", default="importance")
    except Exception:
        return "importance"


def _parse_article(filepath: str) -> ArticleMeta | None:
    import yaml
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if filepath.endswith('.yaml'):
            fm = yaml.safe_load(content) or {}
            body_text = ""
        elif not content.startswith('---'):
            return None
        else:
            parts = content.split('---', 2)
            if len(parts) < 2:
                return None
            fm = yaml.safe_load(parts[1]) or {}
            body_text = parts[2] if len(parts) > 2 else ""
        related = fm.get('related', [])
        # Normalize: strings → {slug, type: see-also}
        normalized = []
        for r in related:
            if isinstance(r, str):
                normalized.append({"slug": r, "type": "see-also"})
            elif isinstance(r, dict):
                if "type" not in r:
                    r = dict(r, type="see-also")
                normalized.append(r)

        # v2: body word count — strip frontmatter and the ## Related section.
        # Scoped to the ## Related section ONLY (up to the next ## heading) so
        # user-authored content below it (e.g. ## Notes) is still counted.
        body = re.sub(r'\n## Related\n.*?(?=\n## |\Z)', '', body_text, flags=re.DOTALL)
        body_words = len(body.split())

        # Defensive coercions (a malformed scalar must not drop the article from the link graph)
        conf = fm.get('confidence', 0.8)
        try:
            confidence = float(conf) if conf is not None else 0.8
        except (TypeError, ValueError):
            logger.warning(f"Malformed confidence in {filepath}: {conf!r} — defaulting to 0.8")
            confidence = 0.8
        rc = fm.get('retrieval_count', 0)
        try:
            retrieval_count = int(rc) if rc is not None else 0
        except (TypeError, ValueError):
            logger.warning(f"Malformed retrieval_count in {filepath}: {rc!r} — defaulting to 0")
            retrieval_count = 0
        imp = fm.get(_get_explicit_importance_field())
        try:
            importance = int(imp) if imp is not None else None
        except (TypeError, ValueError):
            logger.warning(f"Malformed importance in {filepath}: {imp!r} — deriving from signals")
            importance = None

        # Cross-tier duplicate keywords: keep the article-tier copy, drop the
        # subject copy with a warning (mirrors the schema validator
        # check_keyword_tiers, §1.1 — a hand-edited file must not double-count).
        keywords = set(fm.get('keywords', []) or [])
        subject_keywords = set(fm.get('subject_keywords', []) or [])
        dup = keywords & subject_keywords
        if dup:
            subject_keywords = subject_keywords - dup
            logger.warning(f"Cross-tier duplicate keyword(s) in {filepath}: "
                           f"{sorted(dup)} — keeping article-tier copy, dropping subject copy")

        return ArticleMeta(
            slug=fm.get('slug', Path(filepath).stem),
            filepath=filepath,
            keywords=keywords,
            related=normalized,
            title=fm.get('title', ''),
            subject_keywords=subject_keywords,
            article_type=fm.get('type', 'base'),
            body_words=body_words,
            confidence=confidence,
            retrieval_count=retrieval_count,
            lifecycle=fm.get('lifecycle', 'current'),
            importance=importance,
            related_pinned=set(fm.get('related_pinned', [])),
        )
    except Exception as e:
        logger.warning(f"Parse error {filepath}: {e}")
        return None


def _get_linking_config() -> tuple:
    """Return (bridge_threshold, idf_link_threshold) from config."""
    try:
        from ai_kos.config import get
        bridge = get("linking", "bridge_threshold", default=0.20)
        idf_thresh = get("linking", "idf_link_threshold", default=5.5)
        return bridge, idf_thresh
    except Exception:
        return 0.20, 5.5


def _get_v2_linking_config() -> dict:
    """Similarity-mode config keys with §1.8 defaults (works without config.yaml)."""
    from ai_kos.config import get
    return {
        "mode": get("linking", "mode", default="similarity"),
        "similarity_threshold": get("linking", "similarity_threshold", default=0.10),
        "tier_weights": get("linking", "tier_weights",
                            default={"subject": 0.6, "article": 1.4}),
        "min_evidence": get("linking", "min_evidence",
                            default={"shared_article_keywords": 1, "shared_subject_keywords": 3}),
        "subject_df_floor": get("linking", "subject_df_floor", default=0),
        "subject_seed_lexicon": get("linking", "subject_seed_lexicon", default=[]),
        "orphan_rescue": get("linking", "orphan_rescue", default=True),
        "orphan_rescue_floor": get("linking", "orphan_rescue_floor", default=0.10),
        "link_budget": get("linking", "link_budget", default={
            "min_cap": 3, "max_cap": 20,
            "type_base": {"mission": 12, "base": 10, "help": 8, "process": 8,
                          "plan": 6, "procedure": 6, "research-note": 5, "note": 4},
            "length_factor": {"floor": 0.5, "ceiling": 1.25, "words_per_unit": 600},
            "importance": {"explicit_field": "importance", "derived": True},
        }),
        "merge": get("linking", "merge",
                     default={"article_tier_jaccard_threshold": 0.70,
                              "legacy_overlap_threshold": 0.80}),
    }


# ── v2 similarity-mode core (all additive, §2.2.4) ──────────────────────────

def _document_frequencies(articles: List[ArticleMeta]) -> Dict[str, int]:
    """Corpus-wide document frequency over ALL keyword tiers (flat union)."""
    df: Dict[str, int] = {}
    for a in articles:
        for kw in a.all_keywords:
            df[kw] = df.get(kw, 0) + 1
    return df


def _classify_tiers(articles: List[ArticleMeta], subject_df_floor: int | None = None,
                    seed_lexicon: List[str] | None = None) -> None:
    """Classify subject-tier keywords in place (link-time fallback, §1.1).

    Explicit author `subject_keywords` always win (override). Otherwise a keyword
    is subject-tier iff df(k) >= (floor or ceil(sqrt(N))) or k is in the seed
    lexicon. Subject keywords are MOVED from the article tier to the subject tier;
    the all-subject corner keeps the top-3-by-idf keywords as article tier so no
    article ends up keyword-less.
    """
    n = len(articles)
    floor = subject_df_floor if subject_df_floor and subject_df_floor > 0 else math.ceil(math.sqrt(n))
    df = _document_frequencies(articles)
    seeds = set(seed_lexicon or [])
    for a in articles:
        if a.subject_keywords:
            continue  # explicit author override wins
        subject = {k for k in a.keywords if df.get(k, 0) >= floor or k in seeds}
        if not subject:
            continue
        remaining = a.keywords - subject
        if not remaining:
            # All-subject corner: keep top-3-by-idf (rarest, most specific) as article tier.
            idf = {k: math.log((n + 1) / (df.get(k, 0) + 1)) + 1.0 for k in subject}
            top = sorted(subject, key=lambda k: (-idf[k], k))[:3]
            a.keywords = set(top)
            a.subject_keywords = subject - set(top)
        else:
            a.keywords = remaining
            a.subject_keywords = subject


def _build_vectors(articles: List[ArticleMeta], tier_weights: dict) -> Dict[str, Tuple[Dict[str, float], float]]:
    """Sparse tier×IDF keyword vectors: {slug: (weights, norm)} (§1.2).

    weight(k) = tier_weight[tier(k)] × idf(k), where tier is per-article.
    """
    n = len(articles)
    df = _document_frequencies(articles)
    idf = {k: math.log((n + 1) / (count + 1)) + 1.0 for k, count in df.items()}
    w_subject = tier_weights.get("subject", 0.6)
    w_article = tier_weights.get("article", 1.4)
    vectors: Dict[str, Tuple[Dict[str, float], float]] = {}
    for a in articles:
        weights: Dict[str, float] = {}
        for k in a.keywords:
            weights[k] = w_article * idf.get(k, 1.0)
        for k in a.subject_keywords:
            weights[k] = w_subject * idf.get(k, 1.0)
        norm = math.sqrt(sum(v * v for v in weights.values()))
        vectors[a.slug] = (weights, norm)
    return vectors


def _rank_candidates(articles: List[ArticleMeta], vectors: Dict[str, Tuple[Dict[str, float], float]],
                     min_evidence: dict, threshold: float) -> Dict[str, List[Tuple[float, str]]]:
    """Inverted-index-pruned candidate ranking with the min-evidence gate (§1.2).

    Returns {slug: [(score, other_slug), ...]} sorted by (score desc, slug asc) —
    fully deterministic and idempotent.
    """
    inverted: Dict[str, List[str]] = {}
    for a in articles:
        for k in a.all_keywords:
            inverted.setdefault(k, []).append(a.slug)

    by_slug: Dict[str, ArticleMeta] = {a.slug: a for a in articles}
    min_article = min_evidence.get("shared_article_keywords", 1)
    min_subject = min_evidence.get("shared_subject_keywords", 3)
    ranked: Dict[str, List[Tuple[float, str]]] = {a.slug: [] for a in articles}
    pairs_seen: Set[Tuple[str, str]] = set()

    for a in articles:
        va, na = vectors[a.slug]
        if na == 0:
            continue
        for k in va:
            for b_slug in inverted.get(k, []):
                if b_slug == a.slug:
                    continue
                key = tuple(sorted((a.slug, b_slug)))
                if key in pairs_seen:
                    continue
                pairs_seen.add(key)
                vb, nb = vectors[b_slug]
                if nb == 0:
                    continue
                b = by_slug[b_slug]
                shared = set(va) & set(vb)
                shared_article = shared & a.keywords & b.keywords
                shared_subject = shared & a.subject_keywords & b.subject_keywords
                if len(shared_article) < min_article and len(shared_subject) < min_subject:
                    continue
                # Iterate in sorted order: float summation over a `set` varies
                # with PYTHONHASHSEED and could flip scores sitting exactly on
                # the threshold across processes (§5.8 determinism).
                dot = sum(va[k] * vb[k] for k in sorted(shared))
                score = dot / (na * nb)
                if score >= threshold:
                    ranked[a.slug].append((score, b_slug))
                    ranked[b_slug].append((score, a.slug))

    for slug in ranked:
        ranked[slug].sort(key=lambda t: (-t[0], t[1]))
    return ranked


def _select_mutual_topk(articles: List[ArticleMeta], ranked: Dict[str, List[Tuple[float, str]]],
                        budgets: Dict[str, int], rescue: bool = True,
                        rescue_floor: float = 0.10) -> Set[Tuple[str, str]]:
    """Mutual top-k edge selection + orphan rescue (§1.4, §1.7).

    An edge exists iff both endpoints rank each other within their budgets.
    Orphan rescue: an article left with zero edges that has a candidate at or
    above the rescue floor gets its single best candidate linked, subject to the
    partner's remaining budget. Returns undirected edges as sorted (a, b) tuples.
    """
    top: Dict[str, List[str]] = {}
    for a in articles:
        top[a.slug] = [slug for _, slug in ranked[a.slug][: budgets.get(a.slug, 3)]]

    edges: Set[Tuple[str, str]] = set()
    for a in articles:
        for b_slug in top[a.slug]:
            if a.slug in top.get(b_slug, []):
                edges.add(tuple(sorted((a.slug, b_slug))))

    if rescue:
        incident: Dict[str, int] = {}
        for x, y in edges:
            incident[x] = incident.get(x, 0) + 1
            incident[y] = incident.get(y, 0) + 1
        linked = set(incident)
        for a in articles:
            if a.slug in linked or not ranked[a.slug]:
                continue
            best_score, best_slug = ranked[a.slug][0]
            if best_score < rescue_floor:
                continue
            # NOTE: the partner check uses TOTAL incident degree (inbound +
            # outbound), not out-degree. Budgets cap outbound see-also edges,
            # so this is a conservative approximation that can block a rescue
            # onto a partner with many inbound edges but free out-budget —
            # deliberate (prevents inbound hub pile-up), documented per audit.
            if incident.get(best_slug, 0) >= budgets.get(best_slug, 3):
                continue  # partner's budget is exhausted
            edges.add(tuple(sorted((a.slug, best_slug))))
            incident[a.slug] = incident.get(a.slug, 0) + 1
            incident[best_slug] = incident.get(best_slug, 0) + 1
    return edges


def _compute_merge_candidates_v2(articles: List[ArticleMeta],
                                 merge_cfg: dict | None = None) -> List[Tuple[str, str, float]]:
    """Tier-aware merge detection (§1.6).

    merge_candidate(a,b) ⇔ article-tier Jaccard ≥ 0.70 OR legacy full-union
    (keywords ∪ subject_keywords) overlap / min-size ≥ 0.80. The legacy branch
    runs on the full union — identical to today's flat `keywords` — so existing
    supersession behavior is preserved exactly.
    """
    if merge_cfg is None:
        merge_cfg = _get_v2_linking_config()["merge"]
    jaccard_th = merge_cfg.get("article_tier_jaccard_threshold", 0.70)
    legacy_th = merge_cfg.get("legacy_overlap_threshold", 0.80)
    candidates: List[Tuple[str, str, float]] = []
    for i, a in enumerate(articles):
        for j in range(i + 1, len(articles)):
            b = articles[j]
            union_art = a.keywords | b.keywords
            jac = (len(a.keywords & b.keywords) / len(union_art)) if union_art else 0.0
            ua, ub = a.all_keywords, b.all_keywords
            min_size = min(len(ua), len(ub))
            ratio = (len(ua & ub) / min_size) if min_size else 0.0
            if jac >= jaccard_th or ratio > legacy_th:
                # NOTE: `>` (not `>=`) on the legacy branch deliberately
                # preserves the v1.8 boundary (MERGE_THRESHOLD 0.80, strict
                # `>` in `_calculate_links`) — byte-identical legacy behavior.
                # The article-tier Jaccard branch uses `>=` per plan §1.6.
                candidates.append((a.slug, b.slug, round(max(jac, ratio), 2)))
    return candidates


def _calculate_links_v2(articles: List[ArticleMeta],
                        threshold: float | None = None,
                        tier_weights: dict | None = None,
                        min_evidence: dict | None = None,
                        budget_cfg: dict | None = None,
                        rescue: bool | None = None) -> Tuple[Dict[str, Set[str]], List[Tuple[str, str, float]]]:
    """Similarity-mode link computation (v2, §1.2-§1.7).

    Returns (new_links, merge_candidates) — the same contract as _calculate_links.
    Any None param falls back to the §1.8 config value (via
    `_get_v2_linking_config`) — including `similarity_threshold` and
    `orphan_rescue`, so config-driven tuning is honored through the
    `_calculate_links` dispatcher and `link_all`.
    """
    cfg = _get_v2_linking_config()
    if tier_weights is None:
        tier_weights = cfg["tier_weights"]
    if min_evidence is None:
        min_evidence = cfg["min_evidence"]
    if budget_cfg is None:
        budget_cfg = cfg["link_budget"]
    merge_cfg = cfg["merge"]
    if threshold is None:
        threshold = cfg["similarity_threshold"]
    if rescue is None:
        rescue = bool(cfg.get("orphan_rescue", True))
    assert threshold is not None  # narrow for type checker

    _classify_tiers(articles, subject_df_floor=cfg["subject_df_floor"],
                    seed_lexicon=cfg["subject_seed_lexicon"])

    vectors = _build_vectors(articles, tier_weights)
    budgets = {a.slug: _link_budget(a, budget_cfg) for a in articles}
    ranked = _rank_candidates(articles, vectors, min_evidence, threshold)
    edges = _select_mutual_topk(articles, ranked, budgets,
                                rescue=rescue, rescue_floor=cfg["orphan_rescue_floor"])
    merge_candidates = _compute_merge_candidates_v2(articles, merge_cfg)

    new_links: Dict[str, Set[str]] = {a.slug: set() for a in articles}
    for x, y in edges:
        new_links[x].add(y)
        new_links[y].add(x)
    return new_links, merge_candidates


def _importance(meta: ArticleMeta, imp_cfg: dict) -> float:
    """Importance factor (§1.3): explicit 1-5 override → clip(i/3.0, 0.5, 1.5);
    else derived 1.0 + 0.2[conf ≥ 0.9] + 0.2[retrieval ≥ 10] − 0.5[superseded], clipped."""
    if meta.importance is not None:
        return min(max(meta.importance / 3.0, 0.5), 1.5)
    if not imp_cfg.get("derived", True):
        return 1.0
    imp = 1.0
    if meta.confidence >= 0.9:
        imp += 0.2
    if meta.retrieval_count >= 10:
        imp += 0.2
    if meta.lifecycle == "superseded":
        imp -= 0.5
    return min(max(imp, 0.5), 1.5)


def _link_budget(meta: ArticleMeta, budget_cfg: dict) -> int:
    """Per-article see-also cap: clip(round(type_base × lf(L) × imp), min_cap, max_cap) (§1.3).

    lf(L) = clip(0.5 + L/words_per_unit, floor, ceiling); L = body_words (0 for .yaml stubs).
    """
    type_base = budget_cfg.get("type_base", {})
    base = type_base.get(meta.article_type, 5)
    lf_cfg = budget_cfg.get("length_factor", {})
    lf = 0.5 + meta.body_words / lf_cfg.get("words_per_unit", 600)
    lf = min(max(lf, lf_cfg.get("floor", 0.5)), lf_cfg.get("ceiling", 1.25))
    imp = _importance(meta, budget_cfg.get("importance", {}))
    budget = int(round(base * lf * imp))
    min_cap = budget_cfg.get("min_cap", 3)
    max_cap = budget_cfg.get("max_cap", 20)
    return min(max(budget, min_cap), max_cap)


def _calculate_links(articles: List[ArticleMeta], min_overlap: int = 2,
                     idf_threshold: float | None = None,
                     mode: str | None = None) -> tuple:
    """For each article, compute typed edges.

    Mode dispatch (backward-compatible, §2.2.3): the `mode` param wins; else
    `idf_threshold` not None ⇒ legacy (`"idf"` if > 0 else `"count"`); else the
    configured `linking.mode`. `"similarity"` delegates to `_calculate_links_v2`;
    `"idf"`/`"count"` run the legacy v1.8 path byte-for-byte.

    v1.8 legacy modes:
      - IDF-weighted (idf_link_threshold > 0): link if sum of IDF weights
        of shared keywords >= threshold. Common keywords (tda, persistent-homology)
        contribute less; rare keywords (perslay, flood-complex) contribute more.
      - Count-based (idf_link_threshold = 0, legacy): link if >= min_overlap
        shared keywords after excluding bridge keywords.

    Bridge keywords (>bridge_threshold of articles, min 10) are always excluded
    in the legacy modes. Merge detection uses ALL keywords regardless of mode.
    """
    if mode is None:
        if idf_threshold is not None:
            mode = "idf" if idf_threshold > 0 else "count"
        else:
            mode = _get_linking_mode()
    if mode == "similarity":
        return _calculate_links_v2(articles)
    if mode == "count":
        idf_threshold = 0  # explicit count mode: force the count path (config idf may be > 0)

    total = len(articles)

    # --- Bridge keyword detection ---
    bridge_threshold, cfg_idf_threshold = _get_linking_config()
    if idf_threshold is None:
        idf_threshold = cfg_idf_threshold
    assert idf_threshold is not None  # narrow for type checker
    kw_counts: Dict[str, int] = {}
    for a in articles:
        for kw in a.keywords:
            kw_counts[kw] = kw_counts.get(kw, 0) + 1
    bridge_kws: Set[str] = set()
    if total >= 10:
        bridge_kws = {kw for kw, count in kw_counts.items()
                      if count > total * bridge_threshold}
    if bridge_kws:
        logger.debug(f"Bridge keywords excluded: {sorted(bridge_kws)}")

    # --- IDF weights (only needed in IDF mode) ---
    idf: Dict[str, float] = {}
    if idf_threshold > 0:
        for kw, count in kw_counts.items():
            if kw not in bridge_kws:
                idf[kw] = math.log((total + 1) / (count + 1)) + 1.0

    new_links: Dict[str, Set[str]] = {a.slug: set() for a in articles}
    merge_candidates: List[Tuple[str, str, float]] = []

    for i, a in enumerate(articles):
        for j in range(i + 1, len(articles)):
            b = articles[j]
            overlap = a.keywords & b.keywords
            meaningful = overlap - bridge_kws

            if idf_threshold > 0:
                # IDF-weighted mode: sum weights of meaningful keywords
                score = sum(idf.get(kw, 0) for kw in meaningful)
                if score >= idf_threshold:
                    new_links[a.slug].add(b.slug)
                    new_links[b.slug].add(a.slug)
            else:
                # Legacy count-based mode
                if len(meaningful) >= min_overlap:
                    new_links[a.slug].add(b.slug)
                    new_links[b.slug].add(a.slug)

            if a.keywords and b.keywords:
                min_size = min(len(a.keywords), len(b.keywords))
                if min_size > 0:
                    ratio = len(overlap) / min_size
                    if ratio > MERGE_THRESHOLD:
                        merge_candidates.append((a.slug, b.slug, round(ratio, 2)))

    return new_links, merge_candidates


def _compute_link_counts(articles: List[ArticleMeta]) -> Dict[str, int]:
    """Count inbound wikilinks for each article."""
    counts: Dict[str, int] = {a.slug: 0 for a in articles}
    for a in articles:
        for target_slug in a.related_slugs():
            if target_slug in counts:
                counts[target_slug] += 1
    return counts


def _patch_file(
    filepath: str,
    article: ArticleMeta,
    new_related_slugs: Set[str],
    link_count: int = 0,
    superseded_by: str | None = None,
    lifecycle: str | None = None,
    link_budget: int | None = None,
) -> bool:
    """Update related, link_count, and optionally lifecycle/superseded_by/link_budget in frontmatter.

    v2 (§2.2.6): writes `related = sorted(auto_see_also ∪ pinned ∪ manual_non_see_also)` —
    auto edges come from the algorithm, pinned see-also edges from `article.related_pinned`
    (exempt from the budget and preserved regardless of algorithm output), and manual
    non-see-also edges (parent-child, supersedes, …) are preserved exactly as before.
    Unpinned stale see-also edges are dropped. `link_budget` is written when not None.
    """
    try:
        import yaml

        with open(filepath, 'r') as f:
            content = f.read()

        is_yaml = filepath.endswith('.yaml')

        if is_yaml:
            fm = yaml.safe_load(content) or {}
        elif not content.startswith('---'):
            return False
        else:
            parts = content.split('---', 2)
            if len(parts) < 2:
                return False
            fm = yaml.safe_load(parts[1]) or {}

        # Build typed related edges: keep existing types, add new ones as see-also
        existing_by_slug: Dict[str, str] = {}
        for r in fm.get('related', []):
            if isinstance(r, dict):
                existing_by_slug[r.get("slug", "")] = r.get("type", "see-also")
            elif isinstance(r, str):
                existing_by_slug[r] = "see-also"

        # Final edge set: auto ∪ pinned (see-also) ∪ manual non-see-also — sorted by slug
        final: Dict[str, str] = {}
        for slug in new_related_slugs:
            final[slug] = existing_by_slug.get(slug, "see-also")
        for slug in article.related_pinned:
            if slug not in final:
                final[slug] = existing_by_slug.get(slug, "see-also")
        # Also preserve edges where we link TO something not in the overlap set
        # (manually-added edges of other types)
        for slug, etype in existing_by_slug.items():
            if slug not in final and etype != "see-also":
                final[slug] = etype

        new_related = [{"slug": s, "type": final[s]} for s in sorted(final)]

        fm['related'] = new_related
        fm['link_count'] = link_count
        if link_budget is not None:
            fm['link_budget'] = link_budget

        if superseded_by:
            fm['superseded_by'] = superseded_by
            fm['lifecycle'] = 'superseded'
        if lifecycle:
            fm['lifecycle'] = lifecycle

        new_fm = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()

        if is_yaml:
            new_content = new_fm
        else:
            body = parts[2] if len(parts) > 2 else ""
            # Strip ONLY the ## Related section (up to the next ## heading) —
            # the linker owns exactly one ## Related section (always last);
            # user-authored content in any other section (## Notes, etc.) is preserved.
            body = re.sub(r'\n## Related\n.*?(?=\n## |\Z)', '', body, flags=re.DOTALL)
            # Append wikilinks for Obsidian graph view
            if new_related:
                wikilinks = ' '.join(f'[[{r["slug"]}]]' for r in new_related)
                body = body.rstrip() + f'\n\n## Related\n{wikilinks}\n'
            new_content = f"---\n{new_fm}\n---{body}"

        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    except Exception as e:
        logger.error(f"Patch error {filepath}: {e}")
        return False


def link_all(knowledge_dir: str = "knowledge", min_overlap: int | None = None,
             idf_threshold: float | None = None, mode: str | None = None,
             dry_run: bool = False) -> dict:
    """Scan all articles, compute typed links, patch files. Idempotent.

    v1.7: auto-sets lifecycle=superseded on merge losers, computes link_count.
    v2: mode dispatch — the `mode` param wins; else `idf_threshold` not None
    forces the legacy path (`"idf"` if > 0 else `"count"`); else the configured
    `linking.mode`. `"similarity"` runs the tier×IDF v2 pipeline (§1.2-§1.7);
    `"idf"`/`"count"` preserve v1.8 behavior byte-for-byte.
    dry_run=True computes everything, writes nothing, and still returns the full
    report (same shape + `dry_run: True`).

    Report conventions (audit-clarified): `total_links_created` counts DIRECTED
    entries — each undirected edge appears twice — matching the v1.8 convention;
    plan §3.6/§4.2 acceptance targets are UNDIRECTED edge counts (~half).
    `budget_stats.mean_degree`/`orphans` count AUTO edges only (pinned/manual
    edges are excluded from the computed `new_links` set).
    """
    explicit_min_overlap = min_overlap is not None
    if min_overlap is None:
        min_overlap = _get_default_overlap()

    if mode is None:
        if idf_threshold is not None:
            mode = "idf" if idf_threshold > 0 else "count"
        else:
            mode = _get_linking_mode()
    if mode == "similarity" and explicit_min_overlap:
        logger.warning("min_overlap is ignored in similarity mode (accepted for CLI/MCP compat)")

    articles = []
    for ext in ("*.md", "*.yaml"):
        for f in Path(knowledge_dir).rglob(ext):
            meta = _parse_article(str(f))
            # Include pure-subject articles (keywords=[] but subject_keywords
            # non-empty) in similarity mode — §1.2's min-evidence gate supports
            # them (shared_subject ≥ 3). Legacy modes are unchanged.
            if meta and (meta.keywords or (mode == "similarity" and meta.subject_keywords)):
                articles.append(meta)

    if not articles:
        return {"status": "no_articles", "count": 0}

    new_links, merge_candidates = _calculate_links(articles, min_overlap, idf_threshold, mode)
    link_counts = _compute_link_counts(articles)
    # Pinned see-also edges count toward inbound link_count in the same run
    # (§1.5) — they will appear in `related` once patched. Skip pinned targets
    # already reachable via `related` (post-migration backfill, or any re-run
    # after the first) so a pinned edge is never counted twice.
    for a in articles:
        rel = a.related_slugs()
        for target in a.related_pinned:
            if target not in rel and target in link_counts:
                link_counts[target] += 1

    budgets: Dict[str, int] = {}
    if mode == "similarity":
        budgets = {a.slug: _link_budget(a, _get_v2_linking_config()["link_budget"]) for a in articles}

    changes = 0
    # Identify losers in merge pairs (shorter slug is "loser" — heuristic)
    losers: Dict[str, str] = {}
    for a_slug, b_slug, ratio in merge_candidates:
        loser = a_slug if len(a_slug) > len(b_slug) else b_slug
        winner = b_slug if loser == a_slug else a_slug
        losers[loser] = winner

    for article in articles:
        current_slugs = article.related_slugs()
        target_slugs = new_links.get(article.slug, set())
        # Expected final related set: auto ∪ pinned ∪ manual non-see-also (§2.2.6)
        expected_slugs = set(target_slugs) | set(article.related_pinned)
        for r in article.related:
            if isinstance(r, dict) and r.get("type", "see-also") != "see-also":
                expected_slugs.add(r["slug"])

        edge_changed = current_slugs != expected_slugs
        is_loser = article.slug in losers
        # Skip supersede if already superseded to the same winner.
        # Audit fix 2026-08-18: the check used `f.read().split('---')[1]`,
        # which IndexErrors on .yaml whole-dict stubs — a .yaml merge-loser was
        # re-superseded on every run and `articles_changed` never converged.
        # `_read_frontmatter` is extension-aware (whole-dict for .yaml).
        already_superseded = False
        if is_loser:
            try:
                fm = _read_frontmatter(article.filepath)
                if fm.get('lifecycle') == 'superseded' and fm.get('superseded_by') == losers[article.slug]:
                    already_superseded = True
            except Exception:
                pass
        has_supersede = is_loser and not already_superseded
        lc = link_counts.get(article.slug, 0)

        if edge_changed or has_supersede:
            ok = True
            if not dry_run:
                ok = _patch_file(
                    article.filepath, article, target_slugs, link_count=lc,
                    superseded_by=losers.get(article.slug) if has_supersede else None,
                    link_budget=budgets.get(article.slug) if mode == "similarity" else None,
                )
            if ok:
                changes += 1
                logger.info(f"Linked {article.slug}: {len(current_slugs)}→{len(expected_slugs)} edges, link_count={lc}")
        elif not dry_run:
            # Update link_count silently (don't count as a change).
            # Audit fix 2026-08-18: the old `lc != 0` guard skipped the write
            # when the true recomputed count was 0, so a stale positive
            # link_count (inbound links dropped) was never corrected. Write the
            # true recomputed count on every run, including 0.
            _patch_file(
                article.filepath, article, target_slugs, link_count=lc,
                link_budget=budgets.get(article.slug) if mode == "similarity" else None,
            )

    report = {
        "status": "done",
        "articles_scanned": len(articles),
        "articles_changed": changes,
        "total_links_created": sum(len(v) for v in new_links.values()),  # directed (2× undirected) — v1.8 convention
        "merge_candidates": [{"a": a, "b": b, "overlap": r} for a, b, r in merge_candidates],
        "link_mode": mode,
        "idf_threshold": None,
        "min_overlap_used": None,
    }
    if mode == "similarity":
        report["similarity_threshold"] = _get_v2_linking_config()["similarity_threshold"]
        report["budget_stats"] = _budget_stats(budgets, new_links)
    else:
        actual_idf = 0 if mode == "count" else (idf_threshold if idf_threshold is not None else _get_linking_config()[1])
        report["idf_threshold"] = actual_idf if actual_idf > 0 else None
        report["min_overlap_used"] = min_overlap if actual_idf == 0 else None
    if dry_run:
        report["dry_run"] = True
    return report


def _budget_stats(budgets: Dict[str, int], new_links: Dict[str, Set[str]]) -> dict:
    """Budget distribution (min/median/max over per-article budgets) + graph
    out-degree outcomes (mean_degree, orphans) — §2.2.5, §3.6.

    NOTE: mean_degree/orphans are computed over `new_links` (AUTO edges only);
    pinned/manual edges are excluded, so an article with only pinned edges
    counts as an orphan here.
    """
    import statistics
    if not budgets:
        return {"min": 0, "median": 0, "max": 0, "mean_degree": 0.0, "orphans": 0}
    bvals = sorted(budgets.values())
    degrees = [len(v) for v in new_links.values()]
    return {
        "min": bvals[0],
        "median": statistics.median(bvals),
        "max": bvals[-1],
        "mean_degree": round(sum(degrees) / len(degrees), 2) if degrees else 0.0,
        "orphans": sum(1 for d in degrees if d == 0),
    }


def get_linked(slug: str, knowledge_dir: str = "knowledge") -> List[str]:
    for md in Path(knowledge_dir).rglob(f"{slug}.md"):
        meta = _parse_article(str(md))
        if meta:
            return list(meta.related_slugs())
    return []
