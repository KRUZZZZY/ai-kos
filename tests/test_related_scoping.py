"""Regression test for the linker `## Related` scoping fix (2026-08-18).

The linker owns exactly ONE `## Related` section (always regenerated, always last).
User-authored content in any OTHER section (e.g. `## Notes`) must survive link_all.
Prior bug: the strip regex was `\n## Related\n.*` (DOTALL) which wiped everything
after the heading to EOF, destroying any user content below it.
"""
import yaml
from pathlib import Path

from ai_kos.linker import link_all


def _write_md(kd, slug, keywords, body):
    fm = {
        "slug": slug, "title": slug, "type": "base",
        "keywords": keywords, "related": [], "summary": f"About {slug}",
        "schema_version": 2,
    }
    content = f"---\n{yaml.dump(fm, sort_keys=False, default_flow_style=False)}---\n{body}\n"
    p = Path(kd) / f"{slug}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def test_user_content_below_related_survives_link_all(tmp_path):
    kd = tmp_path / "knowledge"
    kd.mkdir()
    # 'a' has user content (## Notes) placed BELOW the ## Related section.
    a = _write_md(kd, "a", ["x", "y", "z"],
                  "Intro paragraph.\n\n## Related\n[[stale]]\n\n"
                  "## Notes\nMy private user notes that must survive.\n")
    # 'b' shares 3 keywords so link_all recomputes a's related (triggers _patch_file).
    _write_md(kd, "b", ["x", "y", "z"], "Another article.\n")

    link_all(str(kd), idf_threshold=0)

    body = a.read_text()
    assert "My private user notes that must survive." in body, \
        "user content below ## Related was destroyed by link_all"
    assert "## Notes" in body
    # the regenerated ## Related section is still present and last
    assert "## Related" in body
    assert body.rstrip().endswith("[[b]]")


def test_body_word_count_includes_content_below_related(tmp_path):
    # The body_words counter must count user content below ## Related (scoped strip),
    # not discard it — so length-based link budgets see the true article length.
    from ai_kos.linker import _parse_article
    a = _write_md(tmp_path, "a", ["x", "y"],
                  "Intro.\n\n## Related\n[[old]]\n\n## Notes\n"
                  + " ".join(f"word{i}" for i in range(50)) + "\n")
    meta = _parse_article(str(a))
    # 50 'wordN' tokens + 'Intro.'/'## Notes' etc. must be well above the 1-word
    # count the old regex would have produced (it would have stripped to just "Intro.").
    assert meta is not None
    assert meta.body_words >= 50, f"expected >=50 words counted, got {meta.body_words}"
