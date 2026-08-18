"""Tests for the AI-KOS v2 linker — similarity mode (tiered keywords, cosine,
link budgets, mutual top-k, orphan rescue, tier-aware merges, tier migration).

Covers plan §4.2 items 1-13. Item 14 (corpus-level acceptance) is deliberately
NOT a unit test — it is `tests/corpus_acceptance.py`, run manually after the
migration + relink (plan §6 steps 15-19).
"""

import copy
import os
import random
import yaml
from datetime import date
from pathlib import Path

import pytest

from ai_kos.linker import (
    ArticleMeta,
    _parse_article,
    _calculate_links,
    _calculate_links_v2,
    _classify_tiers,
    _build_vectors,
    _link_budget,
    _importance,
    _select_mutual_topk,
    _compute_merge_candidates_v2,
    link_all,
)
from ai_kos.migrate import migrate_keyword_tiers, run_migrations

# ── Shared fixtures / helpers ────────────────────────────────────────────────

DEFAULT_TIER_WEIGHTS = {"subject": 0.6, "article": 1.4}
DEFAULT_MIN_EVIDENCE = {"shared_article_keywords": 1, "shared_subject_keywords": 3}
# Plan §1.8 curated seed list (must match ai_kos.config._DEFAULT_CONFIG)
DEFAULT_SEED_LEXICON = [
    "tda", "ai-kos", "persistent-homology", "vectorization", "benchmark",
    "pipeline", "persistence-diagram", "deep-learning", "mcp", "hermes",
    "atq", "sqlite",
]
DEFAULT_BUDGET_CFG = {
    "min_cap": 3,
    "max_cap": 20,
    "type_base": {
        "mission": 12, "base": 10, "help": 8, "process": 8,
        "plan": 6, "procedure": 6, "research-note": 5, "note": 4,
    },
    "length_factor": {"floor": 0.5, "ceiling": 1.25, "words_per_unit": 600},
    "importance": {"explicit_field": "importance", "derived": True},
}
DEFAULT_MERGE_CFG = {
    "article_tier_jaccard_threshold": 0.70,
    "legacy_overlap_threshold": 0.80,
}

# Full §1.8 config with similarity mode (for link_all end-to-end tests)
SIM_CONFIG = {
    "linking": {
        "mode": "similarity",
        "min_keyword_overlap": 2,
        "merge_threshold": 0.80,
        "bridge_threshold": 0.20,
        "idf_link_threshold": 5.5,
        "similarity_threshold": 0.10,  # recalibrated 2026-08-18 — live-corpus sweep (.hermes/linking-rework/calibrate.py): 838 undirected edges, orphans 18, max deg 15 (§3.6 window)
        "tier_weights": DEFAULT_TIER_WEIGHTS,
        "min_evidence": DEFAULT_MIN_EVIDENCE,
        "subject_df_floor": 0,
        "subject_seed_lexicon": DEFAULT_SEED_LEXICON,
        "orphan_rescue": True,
        "orphan_rescue_floor": 0.10,
        "link_budget": DEFAULT_BUDGET_CFG,
        "merge": DEFAULT_MERGE_CFG,
    },
    "article": {
        "max_paragraphs": 5,
        "min_keywords": 3,
        "target_keywords": 10,
        "max_keywords": 15,
        "min_subject_keywords": 2,
        "target_subject_keywords": 5,
        "max_subject_keywords": 8,
        "summary_max_chars": 300,
    },
}


def make_article(path, slug, keywords, subject_keywords=None, related=None,
                 related_pinned=None, type_="base", body="", confidence=0.8,
                 retrieval_count=0, lifecycle="current", importance=None,
                 schema_version=2):
    """Create a temporary markdown article with v2-capable frontmatter."""
    if subject_keywords is None:
        subject_keywords = []
    if related is None:
        related = []
    if related_pinned is None:
        related_pinned = []
    fm = {
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "type": type_,
        "keywords": keywords,
        "related": related,
        "summary": f"Article about {slug}",
        "confidence": confidence,
        "retrieval_count": retrieval_count,
        "lifecycle": lifecycle,
        "schema_version": schema_version,
    }
    # Omit empty tier fields so migration fixtures are not mistaken for
    # already-tier-migrated articles (the tier migration gates on field
    # presence, not schema_version).
    if subject_keywords:
        fm["subject_keywords"] = subject_keywords
    if related_pinned:
        fm["related_pinned"] = related_pinned
    if importance is not None:
        fm["importance"] = importance
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("---\n")
        f.write(yaml.dump(fm, default_flow_style=False, sort_keys=False))
        f.write("---\n\n" + (body or f"Body content about {slug}.\n"))


def meta(slug, keywords, subject=None, type_="base", body_words=0, confidence=0.8,
         retrieval_count=0, lifecycle="current", importance=None, related_pinned=None):
    """ArticleMeta shortcut with explicit tiers (bypasses df-rule classification)."""
    return ArticleMeta(
        slug, "", set(keywords), [],
        subject_keywords=set(subject or []),
        article_type=type_, body_words=body_words, confidence=confidence,
        retrieval_count=retrieval_count, lifecycle=lifecycle,
        importance=importance, related_pinned=set(related_pinned or []),
    )


def cosine(v1, v2):
    """Cosine between two (weights, norm) vectors."""
    w1, n1 = v1
    w2, n2 = v2
    if n1 == 0 or n2 == 0:
        return 0.0
    return sum(w1[k] * w2[k] for k in set(w1) & set(w2)) / (n1 * n2)


@pytest.fixture
def sim_config(tmp_path, monkeypatch):
    """Force linking.mode=similarity (full §1.8 config) for link_all tests."""
    import ai_kos.config as cfg
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(SIM_CONFIG))
    monkeypatch.setattr(cfg, "_find_config", lambda: cfg_file)
    monkeypatch.setattr(cfg, "_config", None)
    return cfg_file


# ── 1. TestTierParsing ───────────────────────────────────────────────────────

class TestTierParsing:
    def test_parse_reads_new_fields(self, tmp_path):
        p = tmp_path / "a.md"
        make_article(str(p), "a", ["x", "y"], subject_keywords=["tda"],
                     related_pinned=["pin1"], importance=4)
        m = _parse_article(str(p))
        assert m is not None
        assert m.subject_keywords == {"tda"}
        assert m.related_pinned == {"pin1"}
        assert m.importance == 4

    def test_missing_fields_have_defaults(self, tmp_path):
        p = tmp_path / "b.md"
        make_article(str(p), "b", ["x", "y"])
        m = _parse_article(str(p))
        assert m is not None
        assert m.subject_keywords == set()
        assert m.related_pinned == set()
        assert m.importance is None
        assert m.article_type == "base"
        assert m.confidence == 0.8
        assert m.retrieval_count == 0
        assert m.lifecycle == "current"

    def test_body_words_excludes_frontmatter_and_related(self, tmp_path):
        p = tmp_path / "c.md"
        body = "alpha beta gamma\n\n## Related\n[[other]]\n"
        make_article(str(p), "c", ["x"], body=body)
        m = _parse_article(str(p))
        assert m is not None
        assert m.body_words == 3  # "alpha beta gamma" only — ## Related stripped

    def test_schema_drops_cross_tier_duplicate_keeps_article_copy(self):
        from ai_kos.schemas import BaseArticle
        a = BaseArticle(content="x", **self._base_data(
            keywords=["tda", "perslay"],
            subject_keywords=["TDA", "ai-kos"],
        ))
        assert a.keywords == ["tda", "perslay"]
        assert a.subject_keywords == ["ai-kos"]  # subject duplicate dropped

    def test_tier_lists_lowercased_and_deduped(self):
        from ai_kos.schemas import BaseArticle
        a = BaseArticle(content="x", **self._base_data(
            keywords=["X", "x", "y"],
            subject_keywords=["AI-KOS", " ai-kos ", "TDA"],
            related_pinned=["Slug", "slug"],
        ))
        assert a.keywords == ["x", "y"]
        assert a.subject_keywords == ["ai-kos", "tda"]
        assert a.related_pinned == ["slug"]

    def test_importance_range_enforced(self):
        from ai_kos.schemas import BaseArticle
        with pytest.raises(ValueError):
            BaseArticle(content="x", **self._base_data(importance=6))

    def test_all_keywords_property(self):
        m = meta("a", ["perslay"], subject=["tda", "ai-kos"])
        assert m.all_keywords == {"perslay", "tda", "ai-kos"}

    def test_malformed_importance_does_not_drop_article(self, tmp_path):
        p = tmp_path / "bad-imp.md"
        make_article(str(p), "bad-imp", ["x", "y"], subject_keywords=["sd"],
                     importance="high")          # hand-edited non-int
        m = _parse_article(str(p))
        assert m is not None                      # article survives parsing
        assert m.importance is None               # falls back to derived
        links, _ = _calculate_links_v2([m, meta("e", ["x", "y"], subject=["se"])], rescue=False)
        assert links["bad-imp"] == {"e"}          # still in the link graph

    def test_malformed_confidence_and_retrieval_coerce_to_defaults(self, tmp_path):
        p = tmp_path / "bad-nums.md"
        make_article(str(p), "bad-nums", ["x"], confidence="high", retrieval_count="many")
        m = _parse_article(str(p))
        assert m is not None
        assert m.confidence == 0.8
        assert m.retrieval_count == 0

    def test_cross_tier_duplicate_dropped_at_parse(self, tmp_path):
        # Mirrors the schema validator: hand-edited file with a keyword in both
        # tiers must not double-count it in vectors/df.
        p = tmp_path / "dup.md"
        make_article(str(p), "dup", ["tda", "perslay"], subject_keywords=["tda", "ai-kos"])
        m = _parse_article(str(p))
        assert m is not None
        assert m.keywords == {"tda", "perslay"}        # article copy kept
        assert m.subject_keywords == {"ai-kos"}        # subject copy dropped

    @staticmethod
    def _base_data(**overrides):
        today = date.today()
        data = {
            "id": "abc", "title": "T", "slug": "t", "type": "base",
            "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": today.replace(year=today.year + 1),
            "keywords": ["a", "b", "c"], "summary": "s",
            "provenance": [{"source": "manual", "origin_ref": "x"}],
        }
        data.update(overrides)
        return data


# ── 2. TestTierClassification ────────────────────────────────────────────────

class TestTierClassification:
    def test_explicit_subject_keywords_respected(self):
        articles = [
            meta("a", ["lowdf"], subject=["explicit-sub"]),
            meta("b", ["lowdf", "other"]),
            meta("c", ["lowdf", "other2"]),
            meta("d", ["lowdf", "other3"]),
        ]
        _classify_tiers(articles)  # N=4, floor=2; "lowdf" df=4 → subject by rule
        a = articles[0]
        assert a.subject_keywords == {"explicit-sub"}   # author override wins
        assert a.keywords == {"lowdf"}                  # untouched by the rule

    def test_df_rule_classifies_subject_tier(self):
        articles = [
            meta("a", ["common", "rare-a"]),
            meta("b", ["common", "rare-b"]),
            meta("c", ["common", "rare-c"]),
            meta("d", ["rare-d"]),
        ]
        _classify_tiers(articles)  # N=4, floor=ceil(sqrt(4))=2
        for a in articles[:3]:
            assert "common" in a.subject_keywords   # df=3 >= 2, moved to subject tier
            assert "rare-a" in a.keywords or "rare-b" in a.keywords or "rare-c" in a.keywords
        d = articles[3]
        assert d.subject_keywords == set()          # no high-df kw here
        assert d.keywords == {"rare-d"}             # article tier untouched

    def test_seed_lexicon_promotes_below_floor_term(self):
        articles = [
            meta("a", ["meta-term", "rare-a"]),
            meta("b", ["rare-b"]),
            meta("c", ["rare-c"]),
            meta("d", ["rare-d"]),
        ]
        _classify_tiers(articles, seed_lexicon=["meta-term"])  # df=1 < floor 2
        assert "meta-term" in articles[0].subject_keywords
        assert "rare-a" in articles[0].keywords

    def test_all_subject_corner_keeps_top3_by_idf(self):
        articles = [
            meta("x", ["g1", "g2", "g3", "g4"]),
            meta("y", ["g1", "g2", "g3", "g4"]),
            meta("z", ["g1", "g2", "g3", "g4"]),
        ]
        _classify_tiers(articles)  # N=3, floor=2 — every kw df=3 → all subject
        for a in articles:
            assert a.keywords == {"g1", "g2", "g3"}   # top-3-by-idf (tie → slug asc)
            assert a.subject_keywords == {"g4"}
            assert a.all_keywords == {"g1", "g2", "g3", "g4"}  # no loss


# ── 3. TestSimilarityMath ────────────────────────────────────────────────────

class TestSimilarityMath:
    def test_two_identical_single_keyword_cosine_one(self):
        a = meta("a", ["perslay"])
        b = meta("b", ["perslay"])
        vectors = _build_vectors([a, b], DEFAULT_TIER_WEIGHTS)
        assert cosine(vectors["a"], vectors["b"]) == pytest.approx(1.0)

    def test_orthogonal_zero(self):
        a = meta("a", ["perslay"])
        b = meta("b", ["flood-complex"])
        vectors = _build_vectors([a, b], DEFAULT_TIER_WEIGHTS)
        assert cosine(vectors["a"], vectors["b"]) == pytest.approx(0.0)

    def test_one_weak_shared_below_threshold(self):
        # 1 shared common (weak) article kw + 4 unique each → cos ≈ 0.112 < 0.20
        a = meta("a", ["common", "a1", "a2", "a3", "a4"])
        b = meta("b", ["common", "b1", "b2", "b3", "b4"])
        vectors = _build_vectors([a, b], DEFAULT_TIER_WEIGHTS)
        assert cosine(vectors["a"], vectors["b"]) == pytest.approx(0.112, abs=0.005)
        links, _ = _calculate_links_v2([meta("a", ["common", "a1", "a2", "a3", "a4"]),
                                        meta("b", ["common", "b1", "b2", "b3", "b4"])],
                                       rescue=False)
        assert links["a"] == set()

    def test_one_strong_rare_shared_links(self):
        # N=5: 1 shared rare article kw (df=2 → idf 1.69) + 1 unique each → cos ≈ 0.394
        a = meta("a", ["perslay", "a1"])
        b = meta("b", ["perslay", "b1"])
        fillers = [meta(f"f{i}", [f"f{i}1"]) for i in range(3)]
        vectors = _build_vectors([a, b] + fillers, DEFAULT_TIER_WEIGHTS)
        assert cosine(vectors["a"], vectors["b"]) == pytest.approx(0.394, abs=0.005)
        links, _ = _calculate_links_v2(
            [meta("a", ["perslay", "a1"]), meta("b", ["perslay", "b1"])]
            + [meta(f"f{i}", [f"f{i}1"]) for i in range(3)],
            rescue=False,
        )
        assert links["a"] == {"b"}

    def test_symmetry_randomized_tier_assignments(self):
        rng = random.Random(42)
        pool = [f"k{i}" for i in range(12)]
        for _ in range(25):
            ka = set(rng.sample(pool, rng.randint(2, 6)))
            kb = set(rng.sample(pool, rng.randint(2, 6)))
            sa = set(rng.sample(sorted(ka), rng.randint(0, len(ka))))
            sb = set(rng.sample(sorted(kb), rng.randint(0, len(kb))))
            a = meta("a", ka - sa, subject=sa)
            b = meta("b", kb - sb, subject=sb)
            vectors = _build_vectors([a, b], DEFAULT_TIER_WEIGHTS)
            assert cosine(vectors["a"], vectors["b"]) == pytest.approx(
                cosine(vectors["b"], vectors["a"])
            )

    def test_bridge_keywords_not_excluded_in_similarity_mode(self):
        # N=10; "common" appears in 3 articles → legacy bridge (3 > 10*0.2)
        # but df=3 < floor=4 → stays article-tier → similarity mode links on it.
        articles = [
            meta("a", ["common", "a1"]),
            meta("b", ["common", "b1"]),
            meta("c", ["common", "c1"]),
        ] + [meta(f"f{i}", [f"f{i}1"]) for i in range(7)]
        legacy_links, _ = _calculate_links(articles, min_overlap=1, idf_threshold=0)
        assert legacy_links["a"] == set()  # "common" is a bridge → excluded
        v2_links, _ = _calculate_links_v2([meta("a", ["common", "a1"]),
                                           meta("b", ["common", "b1"]),
                                           meta("c", ["common", "c1"])]
                                          + [meta(f"f{i}", [f"f{i}1"]) for i in range(7)],
                                          rescue=False)
        assert "b" in v2_links["a"]


# ── 4. TestMinEvidence ───────────────────────────────────────────────────────

class TestMinEvidence:
    def test_two_shared_subjects_high_cos_no_link(self):
        a = meta("a", [], subject=["s1", "s2"])
        b = meta("b", [], subject=["s1", "s2"])
        links, _ = _calculate_links_v2([a, b], rescue=False)
        assert links["a"] == set()  # cos=1.0 but only 2 shared subjects < 3

    def test_one_shared_article_keyword_links(self):
        a = meta("a", ["x"], subject=["as"])
        b = meta("b", ["x"], subject=["bs"])
        links, _ = _calculate_links_v2([a, b], rescue=False)
        assert "b" in links["a"]

    def test_three_shared_subjects_link(self):
        a = meta("a", ["a1"], subject=["s1", "s2", "s3"])
        b = meta("b", ["b1"], subject=["s1", "s2", "s3"])
        links, _ = _calculate_links_v2([a, b], rescue=False)
        assert "b" in links["a"]

    def test_zero_shared_article_two_subjects_no_link_regardless(self):
        a = meta("a", ["a1"], subject=["s1", "s2"])
        b = meta("b", ["b1"], subject=["s1", "s2"])
        links, _ = _calculate_links_v2([a, b], rescue=False)
        assert links["a"] == set()


# ── 5. TestLinkBudget ────────────────────────────────────────────────────────

class TestLinkBudget:
    def test_worked_examples(self):
        # base 348w conf 0.8 → 10 × 1.08 × 1.0 ≈ 11
        assert _link_budget(meta("a", ["x"], type_="base", body_words=348,
                                  confidence=0.8), DEFAULT_BUDGET_CFG) == 11
        # note 100w conf 0.8 → 4 × 0.67 × 1.0 ≈ 3 (clamped to min_cap 3)
        assert _link_budget(meta("n", ["x"], type_="note", body_words=100,
                                  confidence=0.8), DEFAULT_BUDGET_CFG) == 3
        # superseded process 600w → 8 × 1.25 × 0.5 = 5
        assert _link_budget(meta("p", ["x"], type_="process", body_words=600,
                                  lifecycle="superseded"), DEFAULT_BUDGET_CFG) == 5

    def test_explicit_importance_override(self):
        assert _importance(meta("a", ["x"], importance=3), {}) == pytest.approx(1.0)
        assert _importance(meta("a", ["x"], importance=5), {}) == pytest.approx(1.5)
        assert _importance(meta("a", ["x"], importance=1), {}) == pytest.approx(0.5)
        # 5 → clipped 1.5 in the budget too
        assert _link_budget(meta("a", ["x"], type_="base", body_words=0,
                                  importance=5), DEFAULT_BUDGET_CFG) == 8

    def test_derived_importance_signals(self):
        assert _importance(meta("a", ["x"], confidence=0.95), {}) == pytest.approx(1.2)
        assert _importance(meta("a", ["x"], confidence=0.95, retrieval_count=12), {}) == pytest.approx(1.4)
        assert _importance(meta("a", ["x"], lifecycle="superseded"), {}) == pytest.approx(0.5)
        assert _importance(meta("a", ["x"], confidence=0.95, retrieval_count=12,
                                lifecycle="superseded"), {}) == pytest.approx(0.9)

    def test_clamps_at_min_and_max(self):
        # note, 0 words, neutral → 4 × 0.5 = 2 → clamped to 3
        assert _link_budget(meta("n", ["x"], type_="note", body_words=0),
                            DEFAULT_BUDGET_CFG) == 3
        # mission, 1986w, importance 5 → 12 × 1.25 × 1.5 = 22.5 → clamped to 20
        assert _link_budget(meta("m", ["x"], type_="mission", body_words=1986,
                                  importance=5), DEFAULT_BUDGET_CFG) == 20

    def test_zero_body_words_uses_length_floor(self):
        assert _link_budget(meta("a", ["x"], type_="base", body_words=0),
                            DEFAULT_BUDGET_CFG) == 5  # 10 × 0.5 × 1.0


# ── 6. TestMutualTopK ────────────────────────────────────────────────────────

class TestMutualTopK:
    @staticmethod
    def _ranked(hub_ranks_note=True):
        ranked = {
            "h": [(0.9, "x"), (0.8, "y"), (0.7, "n")],
            "x": [(0.9, "h")],
            "y": [(0.8, "h")],
            "n": [(0.95, "p"), (0.9, "q"), (0.85, "r")],
            "p": [(0.95, "n")],
            "q": [(0.9, "n")],
            "r": [(0.85, "n")],
        }
        if not hub_ranks_note:
            ranked["h"] = [(0.9, "x"), (0.8, "y"), (0.7, "z")]
            ranked["z"] = [(0.7, "h")]
        return ranked

    def test_hub_does_not_force_edge_onto_unwilling_note(self):
        articles = [meta(s, []) for s in ["h", "x", "y", "n", "p", "q", "r"]]
        budgets = {s: 3 for s in ["h", "x", "y", "n", "p", "q", "r"]}
        edges = _select_mutual_topk(articles, self._ranked(), budgets, rescue=False)
        assert ("h", "n") not in edges          # n doesn't rank h
        assert ("h", "x") in edges and ("h", "y") in edges
        assert ("n", "p") in edges and ("n", "q") in edges and ("n", "r") in edges

    def test_one_sided_ranking_rejected(self):
        articles = [meta(s, []) for s in ["h", "x", "y", "n", "z"]]
        budgets = {s: 3 for s in ["h", "x", "y", "n", "z"]}
        edges = _select_mutual_topk(articles, self._ranked(hub_ranks_note=False),
                                    budgets, rescue=False)
        assert ("h", "n") not in edges and ("h", "z") in edges

    def test_out_degree_never_exceeds_budget(self):
        # 3 domains × 10 articles; 4 subject kws each (df=10 ≥ floor 9) + 1 unique.
        articles = []
        for d in range(3):
            for k in range(10):
                slug = f"d{d}-a{k}"
                subjects = [f"d{d}-s{j}" for j in range(4)]
                articles.append(meta(slug, [f"d{d}-u{k}"], subject=subjects,
                                     body_words=100))
        links, _ = _calculate_links_v2(articles)
        budgets = {a.slug: _link_budget(a, DEFAULT_BUDGET_CFG) for a in articles}
        for slug, out in links.items():
            assert len(out) <= budgets[slug]
            assert len(out) <= DEFAULT_BUDGET_CFG["max_cap"]

    def test_tie_break_by_slug_deterministic(self):
        articles = [meta(s, []) for s in ["a", "m", "z"]]
        ranked = {
            "a": [(0.5, "z"), (0.5, "m")],   # equal scores → slug asc: "m"
            "m": [(0.5, "a")],
            "z": [(0.5, "a")],
        }
        # _rank_candidates sorts (score desc, slug asc) before selection
        for s in ranked:
            ranked[s].sort(key=lambda t: (-t[0], t[1]))
        budgets = {s: 1 for s in ["a", "m", "z"]}
        e1 = _select_mutual_topk(articles, ranked, budgets, rescue=False)
        e2 = _select_mutual_topk(articles, ranked, budgets, rescue=False)
        assert e1 == e2
        assert ("a", "m") in e1 and ("a", "z") not in e1

    def test_bidirectional_invariant(self):
        articles = []
        for d in range(3):
            for k in range(10):
                slug = f"d{d}-a{k}"
                articles.append(meta(slug, [f"d{d}-u{k}"],
                                     subject=[f"d{d}-s{j}" for j in range(4)],
                                     body_words=100))
        links, _ = _calculate_links_v2(articles)
        for x, out in links.items():
            for y in out:
                assert x in links[y]  # x ∈ links[y] ⇔ y ∈ links[x]


# ── 7. TestOrphanRescue ──────────────────────────────────────────────────────

class TestOrphanRescue:
    def test_orphan_with_candidate_above_floor_gets_exactly_one_edge(self):
        articles = [meta(s, []) for s in ["a", "b", "c"]]
        ranked = {
            "a": [(0.3, "b")],               # only candidate, above 0.10 floor
            "b": [(0.9, "c")],
            "c": [(0.9, "b")],
        }
        budgets = {s: 3 for s in ["a", "b", "c"]}
        edges = _select_mutual_topk(articles, ranked, budgets, rescue=True)
        assert ("a", "b") in edges           # rescued
        incident_a = [e for e in edges if "a" in e]
        assert len(incident_a) == 1          # exactly one edge

    def test_truly_isolated_article_stays_orphan(self):
        articles = [meta(s, []) for s in ["a", "b"]]
        ranked = {"a": [], "b": [(0.9, "c")]}  # a shares zero keywords with anything
        budgets = {"a": 3, "b": 3, "c": 3}
        edges = _select_mutual_topk(articles, ranked, budgets, rescue=True)
        assert all("a" not in e for e in edges)

    def test_rescue_respects_partner_budget(self):
        # b already at its budget (3 mutual edges) → a cannot be rescued onto b
        articles = [meta(s, []) for s in ["a", "b", "x", "y", "z"]]
        ranked = {
            "a": [(0.3, "b")],
            "b": [(0.9, "x"), (0.9, "y"), (0.9, "z")],
            "x": [(0.9, "b")],
            "y": [(0.9, "b")],
            "z": [(0.9, "b")],
        }
        budgets = {s: 3 for s in ["a", "b", "x", "y", "z"]}
        edges = _select_mutual_topk(articles, ranked, budgets, rescue=True)
        assert ("a", "b") not in edges
        assert len([e for e in edges if "b" in e]) == 3


# ── 8. TestMergeV2 ───────────────────────────────────────────────────────────

class TestMergeV2:
    def test_legacy_branch_still_flags_same_union(self):
        # a:{tda,ph,vec}+{perslay} vs b:{tda,ph,vec}+{perslay} — union ratio 4/4=1.0
        # → still flagged by the legacy branch (regression guarantee, §1.6)
        a = meta("a", ["perslay"], subject=["tda", "ph", "vec"])
        b = meta("b", ["perslay"], subject=["tda", "ph", "vec"])
        candidates = _compute_merge_candidates_v2([a, b], DEFAULT_MERGE_CFG)
        assert len(candidates) == 1
        assert candidates[0][:2] == ("a", "b")

    def test_l6_fixed_different_article_keywords(self):
        # 4 shared subjects of 8 total keywords, different article kws:
        # article Jaccard 0, union ratio 4/8 = 0.5 < 0.80 → NOT merge candidates
        a = meta("a", ["a1", "a2", "a3", "a4"], subject=["s1", "s2", "s3", "s4"])
        b = meta("b", ["b1", "b2", "b3", "b4"], subject=["s1", "s2", "s3", "s4"])
        candidates = _compute_merge_candidates_v2([a, b], DEFAULT_MERGE_CFG)
        assert candidates == []

    def test_near_dup_article_jaccard(self):
        a = meta("a", ["k1", "k2", "k3", "k4", "k5", "k6"])
        b = meta("b", ["k1", "k2", "k3", "k4", "k5", "z"])
        candidates = _compute_merge_candidates_v2([a, b], DEFAULT_MERGE_CFG)
        assert len(candidates) == 1  # jaccard 5/7 ≈ 0.714 ≥ 0.70

    def test_identical_flat_keyword_pair_as_before(self):
        a = meta("a", ["x", "y", "z", "w"])
        b = meta("b", ["x", "y", "z", "w"])
        candidates = _compute_merge_candidates_v2([a, b], DEFAULT_MERGE_CFG)
        assert len(candidates) == 1
        assert candidates[0][2] == 1.0  # ratio 1.0 — exactly as before the rework


# ── 9. TestManualEdgePreservation ────────────────────────────────────────────

class TestManualEdgePreservation:
    def _build(self, tmp_path):
        kd = tmp_path / "knowledge"
        kd.mkdir()
        make_article(str(kd / "m1.md"), "m1", ["a1", "a2"], subject_keywords=["s1"],
                     type_="note",
                     related=[{"slug": "parent", "type": "parent-child"}],
                     related_pinned=["pin1", "pin2"])
        make_article(str(kd / "m2.md"), "m2", ["a1", "a2"], subject_keywords=["s1"],
                     related=["stale"])          # unpinned stale see-also
        make_article(str(kd / "parent.md"), "parent", ["p1"], subject_keywords=["s1"])
        make_article(str(kd / "pin1.md"), "pin1", ["q1"], subject_keywords=["s1"])
        make_article(str(kd / "pin2.md"), "pin2", ["q3"], subject_keywords=["s1"])
        make_article(str(kd / "stale.md"), "stale", ["q2"], subject_keywords=["s1"])
        return kd

    def test_manual_and_pinned_edges_survive_unpinned_dropped(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        report = link_all(str(kd), mode="similarity")
        assert report["articles_changed"] > 0

        fm1 = yaml.safe_load((kd / "m1.md").read_text().split("---")[1])
        slugs = {r["slug"] for r in fm1["related"]}
        types = {r["slug"]: r["type"] for r in fm1["related"]}
        assert slugs == {"m2", "parent", "pin1", "pin2"}
        assert types["parent"] == "parent-child"   # manual edge preserved w/ type
        assert types["pin1"] == "see-also" and types["pin2"] == "see-also"

        fm2 = yaml.safe_load((kd / "m2.md").read_text().split("---")[1])
        assert {r["slug"] for r in fm2["related"]} == {"m1"}  # stale dropped

    def test_pinned_edges_exempt_from_budget_and_count_inbound(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        link_all(str(kd), mode="similarity")

        fm1 = yaml.safe_load((kd / "m1.md").read_text().split("---")[1])
        # note + ~4-word body → budget 3, but related holds 4 edges
        # (1 auto + 2 pinned + 1 manual) — pinned/manual don't consume budget
        assert fm1["link_budget"] == 3
        assert len(fm1["related"]) == 4

        fm_pin1 = yaml.safe_load((kd / "pin1.md").read_text().split("---")[1])
        assert fm_pin1["link_count"] == 1        # inbound from m1's pinned edge
        fm_parent = yaml.safe_load((kd / "parent.md").read_text().split("---")[1])
        assert fm_parent["link_count"] == 1      # inbound from m1's manual edge

    def test_idempotent_with_pinned_edges(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        link_all(str(kd), mode="similarity")
        second = link_all(str(kd), mode="similarity")
        assert second["articles_changed"] == 0

    def test_link_count_stable_across_runs_with_pinned_edges(self, tmp_path, sim_config):
        # B1 regression (audit1/2/3): pinned inbound edges were double-counted
        # on every re-run (1 → 2 → 2). link_count must equal true inbound and
        # stay constant across runs; file bytes must be unchanged run 2 → 3.
        kd = self._build(tmp_path)
        link_all(str(kd), mode="similarity")
        fm1 = yaml.safe_load((kd / "pin1.md").read_text().split("---")[1])
        assert fm1["link_count"] == 1              # run 1: fresh pin counted once

        r2 = link_all(str(kd), mode="similarity")
        assert r2["articles_changed"] == 0
        bytes2 = {p: p.read_bytes() for p in kd.rglob("*.md")}

        r3 = link_all(str(kd), mode="similarity")
        assert r3["articles_changed"] == 0
        bytes3 = {p: p.read_bytes() for p in kd.rglob("*.md")}
        assert bytes2 == bytes3                     # file-level idempotency

        fm1_after = yaml.safe_load((kd / "pin1.md").read_text().split("---")[1])
        assert fm1_after["link_count"] == 1         # still 1, not 2

    def test_post_migration_pinned_edge_counted_once(self, tmp_path, sim_config):
        # Post-migration shape: the pinned edge is ALREADY in `related` (as the
        # backfill writes it) — the pinned loop must not count it a second time.
        kd = tmp_path / "kb"
        kd.mkdir()
        make_article(str(kd / "src.md"), "src", ["a1", "a2"], subject_keywords=["s1"],
                     related=[{"slug": "tgt", "type": "see-also"}], related_pinned=["tgt"])
        make_article(str(kd / "tgt.md"), "tgt", ["b1"], subject_keywords=["s1"])
        link_all(str(kd), mode="similarity")
        fm_tgt = yaml.safe_load((kd / "tgt.md").read_text().split("---")[1])
        assert fm_tgt["link_count"] == 1            # once via related, NOT doubled
        r2 = link_all(str(kd), mode="similarity")
        assert r2["articles_changed"] == 0
        fm_tgt2 = yaml.safe_load((kd / "tgt.md").read_text().split("---")[1])
        assert fm_tgt2["link_count"] == 1


# ── 10. TestLinkAllV2 ────────────────────────────────────────────────────────

class TestLinkAllV2:
    def _build(self, tmp_path, name="knowledge"):
        kd = tmp_path / name
        kd.mkdir()
        make_article(str(kd / "a1.md"), "a1", ["x1", "x2"], subject_keywords=["tda", "ai-kos"])
        make_article(str(kd / "a2.md"), "a2", ["x1", "x2", "x3"], subject_keywords=["tda", "ai-kos"])
        make_article(str(kd / "a3.md"), "a3", ["y1", "y2"], subject_keywords=["tda", "ai-kos"])
        make_article(str(kd / "b1.md"), "b1", ["z1", "z2"], subject_keywords=["mlops"])
        return kd

    def test_mode_from_config(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        report = link_all(str(kd))
        assert report["link_mode"] == "similarity"

    def test_dry_run_writes_nothing_but_returns_full_report(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        before = {p: p.read_bytes() for p in kd.rglob("*.md")}
        report = link_all(str(kd), mode="similarity", dry_run=True)
        assert report["dry_run"] is True
        assert report["status"] == "done"
        assert report["articles_changed"] > 0
        assert report["total_links_created"] > 0
        after = {p: p.read_bytes() for p in kd.rglob("*.md")}
        assert before == after                 # nothing written

        real = link_all(str(kd), mode="similarity")
        assert real["articles_changed"] == report["articles_changed"]

    def test_report_contains_v2_keys_and_link_budget_written(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        report = link_all(str(kd), mode="similarity")
        assert report["link_mode"] == "similarity"
        assert report["similarity_threshold"] == 0.10  # recalibrated 2026-08-18 (was 0.20)
        stats = report["budget_stats"]
        assert {"min", "median", "max", "mean_degree", "orphans"} <= set(stats)
        assert stats["min"] >= 3                # budget min_cap
        assert stats["max"] <= 20               # budget max_cap
        assert stats["min"] <= stats["median"] <= stats["max"]

        fm = yaml.safe_load((kd / "a1.md").read_text().split("---")[1])
        assert isinstance(fm["link_budget"], int)
        assert fm["link_budget"] >= 3

    def test_idempotent_second_run(self, tmp_path, sim_config):
        kd = self._build(tmp_path)
        r1 = link_all(str(kd), mode="similarity")
        r2 = link_all(str(kd), mode="similarity")
        assert r2["articles_changed"] == 0
        assert r2["total_links_created"] == r1["total_links_created"]

    def test_legacy_modes_reproduce_legacy_results(self, tmp_path, sim_config):
        kd1, kd2 = self._build(tmp_path, "kb-count-a"), self._build(tmp_path, "kb-count-b")
        r_mode = link_all(str(kd1), mode="count")
        r_arg = link_all(str(kd2), idf_threshold=0)
        assert r_mode["link_mode"] == r_arg["link_mode"] == "count"
        assert r_mode["total_links_created"] == r_arg["total_links_created"]
        assert r_mode["articles_changed"] == r_arg["articles_changed"]

        kd3, kd4 = self._build(tmp_path, "kb-idf-a"), self._build(tmp_path, "kb-idf-b")
        r_mode = link_all(str(kd3), mode="idf")
        r_arg = link_all(str(kd4), idf_threshold=SIM_CONFIG["linking"]["idf_link_threshold"])
        assert r_mode["link_mode"] == r_arg["link_mode"] == "idf"
        assert r_mode == r_arg

    def test_pure_subject_articles_included_in_similarity_mode(self, tmp_path, sim_config):
        # B2 regression (audit1): keywords=[] + subject_keywords non-empty must
        # not be dropped from the graph — §1.2's gate supports them (3 shared
        # subjects link them).
        kd = tmp_path / "kb"
        kd.mkdir()
        make_article(str(kd / "s1.md"), "s1", [],
                     subject_keywords=["tda", "persistent-homology", "vectorization"])
        make_article(str(kd / "s2.md"), "s2", [],
                     subject_keywords=["tda", "persistent-homology", "vectorization"])
        r = link_all(str(kd), mode="similarity")
        assert r["articles_scanned"] == 2
        assert r["total_links_created"] > 0
        # link_count for AUTO edges lands on the second run (it counts inbound
        # from `related`, which run 1 writes; run 2 patches it silently)
        r2 = link_all(str(kd), mode="similarity")
        assert r2["articles_changed"] == 0
        fm1 = yaml.safe_load((kd / "s1.md").read_text().split("---")[1])
        assert {x["slug"] for x in fm1["related"]} == {"s2"}
        assert fm1["link_count"] == 1
        assert isinstance(fm1["link_budget"], int)      # budget written too

    def test_pure_subject_articles_still_excluded_in_legacy_modes(self, tmp_path, sim_config):
        kd = tmp_path / "kb"
        kd.mkdir()
        make_article(str(kd / "s1.md"), "s1", [],
                     subject_keywords=["tda", "persistent-homology", "vectorization"])
        make_article(str(kd / "s2.md"), "s2", [],
                     subject_keywords=["tda", "persistent-homology", "vectorization"])
        r = link_all(str(kd), mode="count")
        assert r["status"] == "no_articles"             # legacy behavior unchanged


# ── Config threading (audit2 §2.3 / audit3 §2.1 regression) ─────────────────

class TestConfigThreading:
    """`similarity_threshold` and `orphan_rescue` config keys must be honored
    through the dispatcher (`link_all` / `_calculate_links(mode="similarity")`),
    not just when passed explicitly."""

    def _write_cfg(self, tmp_path, monkeypatch, overrides):
        import ai_kos.config as cfg
        merged = copy.deepcopy(SIM_CONFIG)
        for k, v in overrides.items():
            merged["linking"][k] = v
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(merged))
        monkeypatch.setattr(cfg, "_find_config", lambda: cfg_file)
        monkeypatch.setattr(cfg, "_config", None)
        return cfg_file

    def test_config_similarity_threshold_honored(self, tmp_path, monkeypatch):
        # Two articles sharing one rare article keyword → cos ≈ 0.34: links at
        # the default 0.10 (recalibrated 2026-08-18; was 0.20), blocked at a configured 0.99.
        def corpus():
            return [
                meta("c1", ["shared", "u1"], subject=["s"]),
                meta("c2", ["shared", "u2"], subject=["s"]),
            ]
        # Default threshold 0.10 → pair links
        self._write_cfg(tmp_path, monkeypatch, {"similarity_threshold": 0.20})
        links, _ = _calculate_links(corpus(), mode="similarity")
        assert "c2" in links["c1"]
        # Configured threshold 0.99 → pair blocked (pre-fix: config ignored)
        self._write_cfg(tmp_path, monkeypatch, {"similarity_threshold": 0.99})
        links2, _ = _calculate_links(corpus(), mode="similarity")
        assert links2["c1"] == set()

    def test_config_similarity_threshold_honored_via_link_all(self, tmp_path, monkeypatch):
        kd = tmp_path / "kb"
        kd.mkdir()
        make_article(str(kd / "c1.md"), "c1", ["shared", "u1"], subject_keywords=["s"])
        make_article(str(kd / "c2.md"), "c2", ["shared", "u2"], subject_keywords=["s"])
        self._write_cfg(tmp_path, monkeypatch, {"similarity_threshold": 0.99})
        r = link_all(str(kd), mode="similarity")
        assert r["similarity_threshold"] == 0.99
        assert r["total_links_created"] == 0            # configured, not hardcoded default

    def test_config_orphan_rescue_honored(self, tmp_path, monkeypatch):
        # 'o' is an orphan whose single best candidate 'p' is above the 0.10
        # floor but outside p's mutual top-k (p prefers q1-q3). Rescue must
        # fire iff config linking.orphan_rescue is true.
        # subject_df_floor=999 freezes classification: no keyword hits the
        # auto floor, so all stay article-tier (keeps scores deterministic).
        def corpus():
            return [
                meta("o", ["wo", "o1", "o2", "o3", "o4", "o5", "o6"], type_="note"),
                meta("p", ["wo", "kp2"], type_="note"),
                meta("q1", ["kp2", "kq1"], type_="note"),
                meta("q2", ["kp2", "kq2"], type_="note"),
                meta("q3", ["kp2", "kq3a", "kq3b", "kq3c"], type_="note"),
                meta("r1", ["kq3a", "kq3b", "kq3c", "kr1"], type_="note"),
                meta("r2", ["kq3a", "kq3b", "kq3c", "kr2"], type_="note"),
                meta("r3", ["kq3a", "kq3b", "kq3c", "kr3"], type_="note"),
            ]
        self._write_cfg(tmp_path, monkeypatch, {"orphan_rescue": False, "subject_df_floor": 999})
        links_off, _ = _calculate_links_v2(corpus())
        assert links_off["o"] == set()                  # not rescued
        self._write_cfg(tmp_path, monkeypatch, {"orphan_rescue": True, "subject_df_floor": 999})
        links_on, _ = _calculate_links_v2(corpus())
        assert links_on["o"] == {"p"}                   # rescued via config


# ── 11. TestConfigCompat ─────────────────────────────────────────────────────

class TestConfigCompat:
    LEGACY_CONFIG = {
        "linking": {
            "min_keyword_overlap": 2, "merge_threshold": 0.80,
            "bridge_threshold": 0.20, "idf_link_threshold": 5.5,
        },
        "article": {
            "max_paragraphs": 5, "min_keywords": 3, "max_keywords": 8,
            "summary_max_chars": 300,
        },
    }

    @pytest.fixture
    def legacy_cfg(self, tmp_path, monkeypatch):
        import ai_kos.config as cfg
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(self.LEGACY_CONFIG))
        monkeypatch.setattr(cfg, "_find_config", lambda: cfg_file)
        monkeypatch.setattr(cfg, "_config", None)
        return cfg_file

    def test_legacy_keys_load_with_new_defaults(self, legacy_cfg):
        from ai_kos.config import load
        c = load()
        linking = c["linking"]
        assert linking["mode"] == "similarity"          # new default
        assert linking["similarity_threshold"] == 0.10  # recalibrated 2026-08-18 (was 0.20)
        assert linking["tier_weights"] == DEFAULT_TIER_WEIGHTS
        assert linking["min_evidence"] == DEFAULT_MIN_EVIDENCE
        assert linking["subject_df_floor"] == 0
        assert linking["subject_seed_lexicon"] == DEFAULT_SEED_LEXICON
        assert linking["orphan_rescue"] is True
        assert linking["orphan_rescue_floor"] == 0.10
        assert linking["link_budget"]["min_cap"] == 3
        assert linking["link_budget"]["max_cap"] == 20
        assert linking["link_budget"]["type_base"]["base"] == 10
        assert linking["merge"] == DEFAULT_MERGE_CFG
        assert linking["min_keyword_overlap"] == 2     # unchanged semantics
        article = c["article"]
        assert article["target_keywords"] == 10        # new defaults present
        assert article["min_subject_keywords"] == 2
        assert article["target_subject_keywords"] == 5
        assert article["max_subject_keywords"] == 8
        assert article["max_keywords"] == 8            # legacy file's value kept — old bounds survive

    def test_legacy_config_behaves_like_explicit_new_defaults(self, legacy_cfg, tmp_path, monkeypatch):
        import ai_kos.config as cfg
        c_legacy = cfg.load()

        full_file = tmp_path / "full.yaml"
        full_file.write_text(yaml.dump(SIM_CONFIG))
        monkeypatch.setattr(cfg, "_find_config", lambda: full_file)
        monkeypatch.setattr(cfg, "_config", None)
        c_full = cfg.load()

        for key in ("similarity_threshold", "tier_weights", "min_evidence",
                    "subject_df_floor", "subject_seed_lexicon", "orphan_rescue",
                    "orphan_rescue_floor", "link_budget", "merge", "mode"):
            assert c_legacy["linking"][key] == c_full["linking"][key]

    def test_subject_df_floor_zero_means_auto(self):
        articles = [meta("a", ["common", "ra"]), meta("b", ["common", "rb"]),
                    meta("c", ["common", "rc"]), meta("d", ["rd"])]
        _classify_tiers(articles, subject_df_floor=0)   # N=4 → auto floor 2
        assert "common" in articles[0].subject_keywords  # df=3 ≥ 2

    def test_positive_floor_honored(self):
        articles = [meta("a", ["common", "ra"]), meta("b", ["common", "rb"]),
                    meta("c", ["common", "rc"]), meta("d", ["rd"])]
        _classify_tiers(articles, subject_df_floor=3)   # df=3 ≥ 3 → still subject
        assert "common" in articles[0].subject_keywords
        articles2 = [meta("a", ["mid", "ra"]), meta("b", ["mid", "rb"]),
                     meta("c", ["rc"]), meta("d", ["rd"])]
        _classify_tiers(articles2, subject_df_floor=3)  # df=2 < 3 → stays article
        assert "mid" in articles2[0].keywords
        assert "mid" not in articles2[0].subject_keywords


# ── 12. TestMigrationTiers ───────────────────────────────────────────────────

class TestMigrationTiers:
    def _build(self, tmp_path):
        d = tmp_path / "knowledge"
        bundles = d / "bundles" / "general"
        bundles.mkdir(parents=True)
        make_article(str(bundles / "alpha.md"), "alpha",
                     ["tda", "ai-kos", "perslay", "flood-complex"],
                     related=["zeta"], schema_version=2)
        make_article(str(bundles / "beta.md"), "beta", ["tda", "ai-kos", "gptzero"],
                     schema_version=2)
        make_article(str(bundles / "gamma.md"), "gamma", ["tda", "ai-kos", "llm"],
                     schema_version=2)
        make_article(str(bundles / "delta.md"), "delta", ["tda", "ai-kos", "mcp"],
                     schema_version=2)
        make_article(str(bundles / "zeta.md"), "zeta", ["zzz"], schema_version=2)
        return d

    def test_dry_run_writes_nothing(self, tmp_path):
        d = self._build(tmp_path)
        before = {p: p.read_bytes() for p in d.rglob("*.md")}
        result = migrate_keyword_tiers(str(d), dry_run=True)
        assert result["status"] == "dry_run"
        assert result["migrated"] == 5
        assert result["skipped"] == 0
        assert result["errors"] == 0
        # tda+ai-kos split in alpha/beta/gamma (2 each); delta's `mcp` is now
        # seed-lexicon-promoted so delta hits the all-subject corner (top-3
        # kept as article tier → 0 subject instances). ≥6 guards the split ran.
        assert result["subject_keyword_instances"] >= 6
        assert all(p.read_bytes() == before[p] for p in before)

    def test_real_run_writes_tiers_pins_and_schema_version(self, tmp_path):
        d = self._build(tmp_path)
        result = migrate_keyword_tiers(str(d))
        assert result["status"] == "done"
        assert result["migrated"] == 5
        assert result["errors"] == 0

        fm = yaml.safe_load((d / "bundles" / "general" / "alpha.md").read_text().split("---")[1])
        assert fm["subject_keywords"] == ["tda", "ai-kos"]
        assert fm["keywords"] == ["perslay", "flood-complex"]
        assert fm["related_pinned"] == ["zeta"]   # see-also edge v2 won't recompute
        assert fm["schema_version"] == 3
        assert fm["history"][-1]["note"] == "tiered-keywords migration"

    def test_no_data_loss_invariant(self, tmp_path):
        d = self._build(tmp_path)
        originals = {}
        for p in d.rglob("*.md"):
            fm = yaml.safe_load(p.read_text().split("---")[1])
            originals[p.name] = set(fm["keywords"])
        migrate_keyword_tiers(str(d))
        for p in d.rglob("*.md"):
            fm = yaml.safe_load(p.read_text().split("---")[1])
            merged = set(fm["keywords"]) | set(fm.get("subject_keywords", []))
            assert merged == originals[p.name]

    def test_all_subject_corner(self, tmp_path):
        d = tmp_path / "kb"
        bundles = d / "bundles" / "general"
        bundles.mkdir(parents=True)
        for slug in ["x", "y", "z"]:
            make_article(str(bundles / f"{slug}.md"), slug, ["g1", "g2", "g3", "g4"],
                         schema_version=2)
        result = migrate_keyword_tiers(str(d))
        assert result["migrated"] == 3
        assert len(result["all_subject_corner"]) == 3
        fm = yaml.safe_load((bundles / "x.md").read_text().split("---")[1])
        assert set(fm["keywords"]) == {"g1", "g2", "g3"}
        assert set(fm["subject_keywords"]) == {"g4"}

    def test_second_run_writes_nothing(self, tmp_path):
        d = self._build(tmp_path)
        migrate_keyword_tiers(str(d))
        second = migrate_keyword_tiers(str(d))
        assert second["migrated"] == 0
        assert second["skipped"] == 5

    def test_run_migrations_tiers_composes(self, tmp_path):
        d = self._build(tmp_path)
        result = run_migrations(knowledge_dir=str(d), tiers=True, dry_run=True)
        assert "tiers" in result
        assert result["tiers"]["status"] == "dry_run"

        result2 = run_migrations(knowledge_dir=str(d), tiers=True)
        assert result2["tiers"]["status"] == "done"
        assert result2["tiers"]["migrated"] == 5
        fm = yaml.safe_load((d / "bundles" / "general" / "beta.md").read_text().split("---")[1])
        assert fm["schema_version"] == 3
        assert "subject_keywords" in fm

        result3 = run_migrations(knowledge_dir=str(d), tiers=True)
        assert result3["tiers"]["migrated"] == 0   # idempotent at the composed level

    def test_schema_version_3_articles_are_still_tiered(self, tmp_path):
        # B2/audit3 regression: the per-file v3 migration stamps schema_version
        # 3 — a version gate would skip tiering these forever. Field-presence
        # gate must still tier them (and pin their legacy edges).
        d = tmp_path / "kb"
        bundles = d / "bundles" / "general"
        bundles.mkdir(parents=True)
        make_article(str(bundles / "a.md"), "a", ["tda", "ai-kos", "perslay"],
                     related=["b"], schema_version=3)
        make_article(str(bundles / "b.md"), "b", ["tda", "ai-kos", "gptzero"],
                     schema_version=3)
        result = migrate_keyword_tiers(str(d))
        assert result["migrated"] == 2
        assert result["skipped"] == 0
        fm = yaml.safe_load((bundles / "a.md").read_text().split("---")[1])
        assert "subject_keywords" in fm
        assert "related_pinned" in fm
        assert fm["schema_version"] == 3

    def test_plain_migrate_then_tiers_still_applies(self, tmp_path):
        # Audit2 repro: a plain run_migrations() stamps sv3 via the per-file
        # v3 migration — the tier pass must still apply afterwards.
        d = self._build(tmp_path)                    # 5 files at sv2
        plain = run_migrations(knowledge_dir=str(d))
        assert plain["migrated"] == 5                # sv2 → sv3 (per-file fields)
        tiers = run_migrations(knowledge_dir=str(d), tiers=True)
        assert tiers["tiers"]["migrated"] == 5
        assert tiers["tiers"]["skipped"] == 0
        fm = yaml.safe_load((d / "bundles" / "general" / "beta.md").read_text().split("---")[1])
        assert "subject_keywords" in fm
        assert "related_pinned" in fm
        assert fm["schema_version"] == 3

    def test_run_migrations_tiers_applies_per_file_migrations_first(self, tmp_path):
        # Audit1 B3 / audit3 §2.2 regression: with tiers=True, the per-file
        # v1/v2/v3 field migrations must run BEFORE the tier pass (otherwise
        # the tier pass stamps sv3 and the per-file loop skips them).
        d = tmp_path / "kb"
        bundles = d / "bundles" / "general"
        bundles.mkdir(parents=True)
        make_article(str(bundles / "old.md"), "old", ["tda", "ai-kos", "perslay"],
                     related=["zeta"], schema_version=1)
        make_article(str(bundles / "zeta.md"), "zeta", ["zzz"], schema_version=1)
        result = run_migrations(knowledge_dir=str(d), tiers=True)
        assert result["tiers"]["migrated"] == 2
        fm = yaml.safe_load((bundles / "old.md").read_text().split("---")[1])
        for field in ("reading_status", "doi", "paper_comparisons"):   # v3 per-file fields
            assert field in fm
        assert "subject_keywords" in fm              # tier split also landed
        assert fm["schema_version"] == 3


# ── 13. TestCalibrationSmoke (slow) ──────────────────────────────────────────

@pytest.mark.slow
class TestCalibrationSmoke:
    @staticmethod
    def _corpus(n_domains=8, per_domain=10, subjects=4):
        """Deterministic ≥50-article fixture: within-domain subject clusters.

        Each article: `subjects` subject kws shared with its domain (df=10 ≥
        floor ceil(sqrt(80))=9 → subject tier) + 1 unique article kw (df=1).
        Within-domain cosine ≈ 0.23 → lands between thresholds 0.18 and 0.22.
        """
        articles = []
        for d in range(n_domains):
            for k in range(per_domain):
                slug = f"d{d}-a{k}"
                articles.append(meta(
                    slug,
                    [f"d{d}-u{k}"],
                    subject=[f"d{d}-s{j}" for j in range(subjects)],
                    body_words=100,
                ))
        return articles

    def test_edge_counts_monotonic_and_deterministic(self):
        counts = {}
        for threshold in (0.18, 0.20, 0.22):
            links, _ = _calculate_links_v2(self._corpus(), threshold=threshold)
            counts[threshold] = sum(len(v) for v in links.values())
        assert counts[0.18] >= counts[0.20] >= counts[0.22]   # non-increasing
        l1, _ = _calculate_links_v2(self._corpus(), threshold=0.20)
        l2, _ = _calculate_links_v2(self._corpus(), threshold=0.20)
        assert l1 == l2                                        # deterministic

    def test_degree_bounds_at_default_threshold(self):
        links, _ = _calculate_links_v2(self._corpus(), threshold=0.20)
        budgets = {a.slug: _link_budget(a, DEFAULT_BUDGET_CFG) for a in self._corpus()}
        degrees = [len(v) for v in links.values()]
        assert max(degrees) <= max(budgets.values()) <= DEFAULT_BUDGET_CFG["max_cap"]
        mean_degree = sum(degrees) / len(degrees)
        assert 3.0 <= mean_degree <= 7.0
