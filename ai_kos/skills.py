"""AI-KOS skill catalog — expose KB articles as loadable skills.

Mirrors DeepSeek Harness' skill capability: a provider registry with layered
discovery, rank-ordered candidates, and a model-facing catalog + loader.
AI-KOS articles ARE the skills: procedure/process/help are how-to skills,
base articles are concept references, research-notes are evidence.

Ranks (dsh rank-order spirit — higher listed first):
  procedure = 100, process = 80, help = 60, base = 40, research-note = 20

Only skill-like article types become skills (notes/plans/missions are not
surfaced). Discovery layers: ``scope`` wins over ``global`` on duplicate names
(nearest-layer-wins). ``invalidate()`` bumps a catalog version so clients can
detect change (skills/change analog).
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("ai-kos.skills")

ARTICLE_RANKS = {
    "procedure": 100,
    "process": 80,
    "help": 60,
    "base": 40,
    "research-note": 20,
}


@dataclass
class SkillCandidate:
    """One discoverable skill in a catalog snapshot."""

    name: str
    description: str
    rank: int
    provider: str
    slug: str


@dataclass
class SkillDefinition:
    """A loaded skill: full body + metadata for the requesting model."""

    name: str
    body: str
    meta: dict


class SkillProvider:
    """Provider contract: list candidates, load a full skill body."""

    name = "base"

    def list(self) -> List[SkillCandidate]:
        raise NotImplementedError

    def get(self, candidate: SkillCandidate) -> Optional[SkillDefinition]:
        raise NotImplementedError


class KBArticleSkillProvider(SkillProvider):
    """AI-KOS knowledge base as a skill source (read-only)."""

    def __init__(self, knowledge_dir: Optional[str] = None):
        self.name = "kb-articles"
        self._knowledge_dir = knowledge_dir

    def _articles(self) -> list:
        from ai_kos.articles import list_articles

        if self._knowledge_dir is None:
            from ai_kos.articles import _refresh_index
            _refresh_index()  # ensure the catalog reflects the current KB, not a stale index
            return list_articles()
        # Test/isolated knowledge dirs: list via the article index in that dir.
        from ai_kos.bindings import kb_path
        from pathlib import Path

        d = Path(kb_path(self._knowledge_dir))
        out = []
        for f in sorted(d.rglob("*.md")):
            text = f.read_text()
            if not text.startswith("---"):
                continue
            parts = text.split("---", 2)
            if len(parts) < 3:
                continue
            import yaml

            fm = yaml.safe_load(parts[1]) or {}
            if "slug" not in fm:
                continue
            out.append({
                "slug": fm["slug"],
                "type": fm.get("type", "note"),
                "title": fm.get("title", fm["slug"]),
                "summary": fm.get("summary", ""),
                "keywords": fm.get("keywords", []),
            })
        return out

    def list(self) -> List[SkillCandidate]:
        out = []
        for a in self._articles():
            atype = a.get("type") or "note"
            rank = ARTICLE_RANKS.get(atype)
            if rank is None:
                continue  # only skill-like article types are skills
            out.append(SkillCandidate(
                name=a["slug"],
                description=(a.get("summary") or a.get("title") or "")[:200],
                rank=rank,
                provider=self.name,
                slug=a["slug"],
            ))
        return out

    def get(self, candidate: SkillCandidate) -> Optional[SkillDefinition]:
        from ai_kos.articles import read_article

        art = read_article(candidate.slug)
        if not art:
            return None
        fm = art.get("frontmatter") or {}
        title = fm.get("title") or candidate.name
        summary = fm.get("summary") or ""
        keywords = fm.get("keywords") or []
        raw_body = art.get("body") or ""

        parts = [f"# {title}"]
        if summary:
            parts.append(f"\n{summary}")
        if keywords:
            parts.append(f"\nKeywords: {', '.join(keywords)}")
        if raw_body:
            parts.append(f"\n{raw_body}")

        meta = {
            "slug": candidate.slug,
            "type": fm.get("type"),
            "title": title,
            "keywords": keywords,
        }
        return SkillDefinition(name=candidate.slug,
                               body="\n".join(parts).strip() + "\n",
                               meta=meta)


class SkillRegistry:
    """Layered provider registry with catalog snapshots + invalidation."""

    def __init__(self):
        self._providers: Dict[str, List[SkillProvider]] = {"global": [], "scope": []}
        self._version = 0

    def register(self, provider: SkillProvider, layer: str = "global") -> None:
        if layer not in self._providers:
            raise ValueError(f"unknown layer: {layer}")
        self._providers[layer].append(provider)
        self.invalidate()

    def catalog(self) -> List[SkillCandidate]:
        """Merged snapshot: scope beats global on name; rank desc, then name."""
        seen: Dict[str, SkillCandidate] = {}
        for layer in ("scope", "global"):
            for p in self._providers.get(layer, []):
                for c in p.list():
                    if c.name not in seen:
                        seen[c.name] = c
        return sorted(seen.values(), key=lambda c: (-c.rank, c.name))

    def load(self, name: str) -> Optional[SkillDefinition]:
        for layer in ("scope", "global"):
            for p in self._providers.get(layer, []):
                for c in p.list():
                    if c.name == name:
                        d = p.get(c)
                        if d is not None:
                            return d
        return None

    def invalidate(self) -> None:
        """Bump the catalog version (skills/change analog)."""
        self._version += 1

    def catalog_version(self) -> int:
        return self._version


_DEFAULT_REGISTRY = SkillRegistry()
_DEFAULT_REGISTRY.register(KBArticleSkillProvider(), layer="global")


def skill_catalog(knowledge_dir: Optional[str] = None) -> List[SkillCandidate]:
    """Convenience: catalog snapshot over the KB article provider."""
    if knowledge_dir is not None:
        reg = SkillRegistry()
        reg.register(KBArticleSkillProvider(knowledge_dir=knowledge_dir), layer="global")
        return reg.catalog()
    return _DEFAULT_REGISTRY.catalog()


def skill_load(name: str, knowledge_dir: Optional[str] = None) -> Optional[SkillDefinition]:
    """Convenience: load one skill by slug."""
    if knowledge_dir is not None:
        reg = SkillRegistry()
        reg.register(KBArticleSkillProvider(knowledge_dir=knowledge_dir), layer="global")
        return reg.load(name)
    return _DEFAULT_REGISTRY.load(name)


def catalog_version() -> int:
    """Current catalog version of the default registry."""
    return _DEFAULT_REGISTRY.catalog_version()
