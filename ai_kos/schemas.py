"""AI-KOS schemas v1.5 — 7 article types with OKF-compliant frontmatter."""

from datetime import date
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Article types ──────────────────────────────────────────────

class ArticleType(str, Enum):
    BASE = "base"               # factoid / Wikipedia-style concept
    PROCESS = "process"         # step-by-step procedure (skill backup)
    PLAN = "plan"               # planning document
    HELP = "help"               # explains part of a project
    RESEARCH_NOTE = "research-note"  # notes for larger research
    NOTE = "note"               # temporary, may relate to future work
    MISSION = "mission"         # project building block

class Stability(str, Enum):
    STABLE = "stable"
    MODERATE = "moderate"
    VOLATILE = "volatile"

class SensitivityLabel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


# ── Individual type models (frontmatter only) ──────────────────

class _BaseFrontmatter(BaseModel):
    """Shared fields across all article types."""
    id: str = Field(..., description="UUID")
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    type: ArticleType
    created_at: date
    updated_at: date
    reviewed_at: date
    next_review_at: date
    stability: Stability = Stability.MODERATE
    sensitivity_label: SensitivityLabel = SensitivityLabel.INTERNAL
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="How certain this knowledge is (0.0-1.0)")
    keywords: List[str] = Field(default_factory=list, description="3-8 lowercase keywords for auto-linking")
    summary: str = Field(..., max_length=300, description="1-2 sentence description")
    related: List[str] = Field(default_factory=list, description="Auto-generated [[wikilinks]] — managed by linker")
    provenance: List[str] = Field(..., min_length=1, description="Original source file(s)")
    ai_notes: Optional[str] = Field(default=None, description="Agent workspace, not shown to humans")
    retrieval_count: int = Field(default=0, ge=0)
    # Gap tracking (known unknowns)
    gap: bool = Field(default=False, description="True = known unknown")
    gap_question: Optional[str] = Field(default=None, description="Required when gap=True")
    gap_priority: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Required when gap=True")
    schema_version: int = Field(default=1, ge=1, description="Schema version for migration tracking")

    @field_validator('keywords')
    @classmethod
    def keywords_lower(cls, v: List[str]) -> List[str]:
        seen = set()
        out = []
        for kw in v:
            kw = kw.lower().strip()
            if kw and kw not in seen:
                seen.add(kw)
                out.append(kw)
        return out

    @model_validator(mode='after')
    def check_gap(self):
        if self.gap and not self.gap_question:
            raise ValueError('gap_question is required when gap=True')
        if self.gap and self.gap_priority is None:
            raise ValueError('gap_priority is required when gap=True')
        return self

    @model_validator(mode='after')
    def check_dates(self):
        if self.reviewed_at < self.created_at: raise ValueError('reviewed_at >= created_at')
        if self.updated_at < self.created_at: raise ValueError('updated_at >= created_at')
        if self.next_review_at < self.updated_at: raise ValueError('next_review_at >= updated_at')
        return self


class BaseArticle(_BaseFrontmatter):
    """Factoid / Wikipedia-style concept article. ~5 paragraphs."""
    type: ArticleType = ArticleType.BASE
    content: str = Field(..., description="5 paragraphs max, concise factual article")

class ProcessArticle(_BaseFrontmatter):
    """Step-by-step procedure. Backup for rarely-used Hermes skills."""
    type: ArticleType = ArticleType.PROCESS
    steps: List[str] = Field(..., min_length=1, description="Ordered steps")
    outcome: str = Field(..., min_length=1, description="What happens when all steps complete")
    prerequisites: List[str] = Field(default_factory=list)

class PlanArticle(_BaseFrontmatter):
    """Planning document — outlines everything for a goal."""
    type: ArticleType = ArticleType.PLAN
    goal: str = Field(..., description="What this plan achieves")
    phases: List[str] = Field(default_factory=list, description="Phase descriptions")
    milestones: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

class HelpArticle(_BaseFrontmatter):
    """Explains how a part of a project works."""
    type: ArticleType = ArticleType.HELP
    project: str = Field(..., description="Which project this helps with")
    component: str = Field(..., description="Specific component explained")
    explanation: str = Field(..., description="~5 paragraphs explaining how it works")
    examples: List[str] = Field(default_factory=list)

class ResearchNoteArticle(_BaseFrontmatter):
    """Key notes for larger research — becomes a base article later."""
    type: ArticleType = ArticleType.RESEARCH_NOTE
    topic: str = Field(..., description="The broader research topic")
    key_notes: List[str] = Field(..., min_length=1, description="Bullet-point notes")
    open_questions: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    target_base_slug: Optional[str] = Field(default=None, description="Slug of base article this feeds into")

class NoteArticle(_BaseFrontmatter):
    """Temporary note — may relate to future work."""
    type: ArticleType = ArticleType.NOTE
    content: str = Field(..., description="The note content, ~5 paragraphs max")
    related_project: Optional[str] = Field(default=None, description="Project this might relate to")
    actionable: bool = Field(default=False, description="Whether this needs follow-up")

class MissionArticle(_BaseFrontmatter):
    """Project building block — explains how a project will work."""
    type: ArticleType = ArticleType.MISSION
    project: str = Field(..., description="The project name")
    purpose: str = Field(..., description="Why this project exists")
    architecture: str = Field(..., description="How it will be built, ~5 paragraphs")
    dependencies: List[str] = Field(default_factory=list, description="Other missions or tools needed")
    success_criteria: List[str] = Field(default_factory=list)


# ── Union type for dispatch ────────────────────────────────────

Article = BaseArticle | ProcessArticle | PlanArticle | HelpArticle | ResearchNoteArticle | NoteArticle | MissionArticle


# ── Template definitions (what the AI uses to generate articles) ─

TEMPLATES = {
    ArticleType.BASE: {
        "description": "Factoid / Wikipedia-style concept. ~5 paragraphs.",
        "ai_layer_fields": ["id","title","slug","type","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["content"],
        "prompt": "Write a concise, factual article (~5 paragraphs). No fluff. Start with a 1-sentence definition, then explain. End with why it matters.",
    },
    ArticleType.PROCESS: {
        "description": "Step-by-step procedure. Backup for rarely-used skills.",
        "ai_layer_fields": ["id","title","slug","type","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["steps","outcome","prerequisites"],
        "prompt": "Write step-by-step instructions. Each step must be an imperative command. End with an outcome statement. List prerequisites if any.",
    },
    ArticleType.PLAN: {
        "description": "Planning document for a goal.",
        "ai_layer_fields": ["id","title","slug","type","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["goal","phases","milestones","risks"],
        "prompt": "Write a planning document. State the goal first. List phases, milestones, and risks. Be specific, not aspirational.",
    },
    ArticleType.HELP: {
        "description": "Explains how a part of a project works.",
        "ai_layer_fields": ["id","title","slug","type","project","component","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["explanation","examples"],
        "prompt": "Explain how a specific component of a project works. Name the project and component. ~5 paragraphs. Include examples if helpful.",
    },
    ArticleType.RESEARCH_NOTE: {
        "description": "Key notes for larger research — feeds into a base article.",
        "ai_layer_fields": ["id","title","slug","type","topic","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["key_notes","open_questions","sources","target_base_slug"],
        "prompt": "Extract key research notes. Use bullet points. List open questions and sources. Note if this feeds into an existing base article.",
    },
    ArticleType.NOTE: {
        "description": "Temporary note — may relate to future work.",
        "ai_layer_fields": ["id","title","slug","type","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["content","related_project","actionable"],
        "prompt": "Write a brief note. ~5 paragraphs max. Flag if actionable. Note any related project. Keep it simple — this is temporary.",
    },
    ArticleType.MISSION: {
        "description": "Project building block — how a project will work.",
        "ai_layer_fields": ["id","title","slug","type","project","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","keywords","summary","related","provenance","ai_notes","retrieval_count"],
        "human_fields": ["purpose","architecture","dependencies","success_criteria"],
        "prompt": "Describe a project mission. State its purpose. Explain the architecture (~5 paragraphs). List dependencies and success criteria.",
    },
}


# ── Helpers ─────────────────────────────────────────────────────

ARTICLE_CLASSES: dict[ArticleType, type] = {
    ArticleType.BASE: BaseArticle,
    ArticleType.PROCESS: ProcessArticle,
    ArticleType.PLAN: PlanArticle,
    ArticleType.HELP: HelpArticle,
    ArticleType.RESEARCH_NOTE: ResearchNoteArticle,
    ArticleType.NOTE: NoteArticle,
    ArticleType.MISSION: MissionArticle,
}

def get_class(article_type: ArticleType | str) -> type:
    if isinstance(article_type, str):
        article_type = ArticleType(article_type)
    return ARTICLE_CLASSES[article_type]

def article_to_markdown(article) -> str:
    """Serialize any article to OKF markdown (YAML frontmatter + body)."""
    import yaml
    data = article.model_dump(mode='json')
    fm = {k: v for k, v in data.items() if v is not None}
    body_fields = TEMPLATES[article.type]["human_fields"]
    body = {}
    for k in body_fields:
        if k in fm:
            body[k] = fm.pop(k)
    # Add Obsidian tags for graph coloring
    fm['tags'] = [f'type/{article.type.value}']
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    body_str = _format_body(body, article.type)
    # Append wikilinks section for Obsidian graph view
    related = fm.get('related', [])
    if related:
        wikilinks = ' '.join(f'[[{r}]]' for r in related)
        body_str += f'\n\n## Related\n{wikilinks}'
    return f"---\n{yaml_str}\n---\n\n{body_str}".strip()

def _format_body(body: dict, atype: ArticleType) -> str:
    """Format the human-readable body based on article type."""
    lines = []
    if atype == ArticleType.BASE:
        lines.append(body.get("content", ""))
    elif atype == ArticleType.PROCESS:
        lines.append(f"## Outcome\n{body.get('outcome','')}\n")
        if body.get("prerequisites"):
            lines.append("## Prerequisites")
            for p in body["prerequisites"]:
                lines.append(f"- {p}")
            lines.append("")
        lines.append("## Steps")
        for i, s in enumerate(body.get("steps", []), 1):
            lines.append(f"{i}. {s}")
    elif atype == ArticleType.PLAN:
        lines.append(f"## Goal\n{body.get('goal','')}\n")
        for section in ["phases", "milestones", "risks"]:
            if body.get(section):
                lines.append(f"## {section.title()}")
                for item in body[section]:
                    lines.append(f"- {item}")
                lines.append("")
    elif atype == ArticleType.HELP:
        lines.append(f"## {body.get('component','Component')}\n{body.get('explanation','')}\n")
        if body.get("examples"):
            lines.append("## Examples")
            for ex in body["examples"]:
                lines.append(f"- {ex}")
    elif atype == ArticleType.RESEARCH_NOTE:
        lines.append(f"## Topic: {body.get('topic','')}\n")
        for section in ["key_notes", "open_questions", "sources"]:
            if body.get(section):
                lines.append(f"## {section.replace('_',' ').title()}")
                for item in body[section]:
                    lines.append(f"- {item}")
                lines.append("")
    elif atype == ArticleType.NOTE:
        lines.append(body.get("content", ""))
    elif atype == ArticleType.MISSION:
        lines.append(f"## Purpose\n{body.get('purpose','')}\n")
        lines.append(f"## Architecture\n{body.get('architecture','')}\n")
        for section in ["dependencies", "success_criteria"]:
            if body.get(section):
                lines.append(f"## {section.replace('_',' ').title()}")
                for item in body[section]:
                    lines.append(f"- {item}")
                lines.append("")
    return "\n".join(lines).strip()
