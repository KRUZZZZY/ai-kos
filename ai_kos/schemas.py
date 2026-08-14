"""AI-KOS schemas v1.7 — 7 article types with typed relations, lifecycle, Diátaxis, and usage signals."""

from datetime import date, datetime
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
    PROCEDURE = "procedure"     # task-specific implementation guide

class Stability(str, Enum):
    STABLE = "stable"
    MODERATE = "moderate"
    VOLATILE = "volatile"

class SensitivityLabel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"

class DocType(str, Enum):
    """Diátaxis framework — how a reader should consume this content. Orthogonal to ArticleType."""
    TUTORIAL = "tutorial"
    HOW_TO = "how-to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"

class Lifecycle(str, Enum):
    """Article lifecycle state."""
    CURRENT = "current"
    SUPERSEDED = "superseded"
    HISTORICAL = "historical"

class ProvenanceSource(str, Enum):
    """How this article was created."""
    INGEST = "ingest"
    RESEARCH_PIPELINE = "research-pipeline"
    MANUAL = "manual"
    IMPORT = "import"
    PROMOTED_FROM_NOTE = "promoted-from-note"

class RelationType(str, Enum):
    """Typed edge between two articles."""
    SEE_ALSO = "see-also"
    PARENT_CHILD = "parent-child"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"

class ReadingStatus(str, Enum):
    """How thoroughly a paper has been read and processed."""
    UNREAD = "unread"
    SKIMMED = "skimmed"
    ANNOTATED = "annotated"
    SYNTHESIZED = "synthesized"

class Backend(str, Enum):
    """Where article body/content is stored."""
    MD = "md"       # markdown in .md file (default)
    SQL = "sql"     # SQL table in datasets/ database
    BLOB = "blob"   # binary file in datasets/blobs/
    JSON = "json"   # JSON document in datasets/
    GRAPH = "graph" # node/edge tables in datasets/


# ── Sub-models ─────────────────────────────────────────────────

class RelatedEdge(BaseModel):
    """A typed wikilink from this article to another."""
    slug: str
    type: RelationType = RelationType.SEE_ALSO

class Provenance(BaseModel):
    """Structured provenance tracking."""
    source: ProvenanceSource = ProvenanceSource.MANUAL
    origin_ref: Optional[str] = None  # pipeline ID, source filename

class VersionEntry(BaseModel):
    """One entry in the content edit history log."""
    v: int
    at: datetime
    by: str
    note: str

class PaperComparison(BaseModel):
    """Records a comparison between two papers: agreement, contradiction, or gap."""
    other_slug: str
    relationship: str  # "agrees", "contradicts", "extends", "gap"
    detail: str = ""   # brief explanation of the relationship

class DatasetColumn(BaseModel):
    """A single column definition for a SQL-backed dataset."""
    name: str
    type: str = "TEXT"  # TEXT, INTEGER, REAL, BLOB

class DatasetRef(BaseModel):
    """Reference to a SQL table that holds this article's body/content."""
    db: str = Field(..., description="Path to the SQLite database file, e.g. datasets/wildlife.db")
    table: str = Field(..., description="Table name, e.g. bird_species")
    columns: List[DatasetColumn] = Field(default_factory=list, description="Column definitions")
    time_column: Optional[str] = Field(default=None, description="Column holding timestamps for time-series data")
    time_resolution: Optional[str] = Field(default=None, description="Expected interval: '5s', '1m', '1h', '1d'")
    json_schema: Optional[dict] = Field(default=None, description="Expected JSON schema shape for documentation")

class BlobRef(BaseModel):
    """Reference to a binary file stored in datasets/blobs/."""
    path: str = Field(..., description="Path to the blob file, e.g. datasets/blobs/screenshot.png")
    mime_type: str = Field(default="application/octet-stream", description="MIME type")
    size_bytes: int = Field(default=0, ge=0, description="File size in bytes")
    extracted_text: str = Field(default="", description="OCR/STT extracted text for search indexing")

class GraphRef(BaseModel):
    """Metadata about a graph dataset stored in SQLite node/edge tables."""
    directed: bool = Field(default=True, description="True for directed graphs")
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)
    node_attributes: List[str] = Field(default_factory=list, description="Column names in nodes table besides node_id")
    edge_attributes: List[str] = Field(default_factory=list, description="Column names in edges table besides source/target")


# ── Default review intervals per article type (days) ───────────

DEFAULT_REVIEW_INTERVALS: dict[ArticleType, int] = {
    ArticleType.BASE: 365,
    ArticleType.PROCESS: 180,
    ArticleType.PLAN: 90,
    ArticleType.HELP: 365,
    ArticleType.RESEARCH_NOTE: 180,
    ArticleType.NOTE: 90,
    ArticleType.MISSION: 365,
}


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
    # v1.7: typed relations
    related: List[RelatedEdge] = Field(default_factory=list, description="Typed wikilinks — managed by linker")
    provenance: List[Provenance] = Field(..., min_length=1, description="Structured provenance records")
    ai_notes: Optional[str] = Field(default=None, description="Agent workspace, not shown to humans")
    # v1.7: usage signals
    retrieval_count: int = Field(default=0, ge=0)
    link_count: int = Field(default=0, ge=0, description="Inbound wikilink count — computed by linker")
    last_accessed: Optional[date] = Field(default=None, description="Last time ai_kos_read was called")
    # v1.7: lifecycle
    lifecycle: Lifecycle = Lifecycle.CURRENT
    superseded_by: Optional[str] = Field(default=None, description="Slug of successor article")
    # v1.7: Diátaxis
    doc_type: Optional[DocType] = Field(default=None, description="Diátaxis consumption mode")
    # v1.7: paper ingestion
    reading_status: ReadingStatus = Field(default=ReadingStatus.UNREAD, description="How thoroughly the paper has been processed")
    doi: Optional[str] = Field(default=None, description="DOI of the source paper")
    paper_comparisons: List[PaperComparison] = Field(default_factory=list, description="Relationships to other papers (agrees, contradicts, extends, gap)")
    # v1.7: review cadence
    review_interval_days: Optional[int] = Field(default=None, ge=1, description="Days between reviews (defaults per type)")
    # v1.7: edit history
    version: int = Field(default=1, ge=1, description="Content edit version counter")
    history: List[VersionEntry] = Field(default_factory=list, description="Compact edit log")
    # Gap tracking (known unknowns)
    gap: bool = Field(default=False, description="True = known unknown")
    gap_question: Optional[str] = Field(default=None, description="Required when gap=True")
    gap_priority: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Required when gap=True")
    schema_version: int = Field(default=2, ge=1, description="Schema version for migration tracking")
    # v1.8: backend storage
    backend: Backend = Field(default=Backend.MD, description="Where content is stored — md file or sql table")
    dataset: Optional[DatasetRef] = Field(default=None, description="SQL table reference when backend=sql")
    blob: Optional[BlobRef] = Field(default=None, description="Binary file reference when backend=blob")
    graph: Optional[GraphRef] = Field(default=None, description="Graph metadata when backend=graph")

    @field_validator('related', mode='before')
    @classmethod
    def _coerce_related(cls, v):
        """Accept bare strings (v1.6 format) and upgrade to RelatedEdge."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"slug": item, "type": "see-also"})
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append(item)
        return result

    @field_validator('provenance', mode='before')
    @classmethod
    def _coerce_provenance(cls, v):
        """Accept bare strings (v1.6 format) and upgrade to Provenance objects."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"source": "manual", "origin_ref": item})
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append(item)
        return result

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
    """Project building block — how a project will work."""
    type: ArticleType = ArticleType.MISSION
    project: str = Field(..., description="The project name")
    purpose: str = Field(..., description="Why this project exists")
    architecture: str = Field(..., description="How it will be built, ~5 paragraphs")
    dependencies: List[str] = Field(default_factory=list, description="Other missions or tools needed")
    success_criteria: List[str] = Field(default_factory=list)


class ProcedureArticle(_BaseFrontmatter):
    """Task-specific implementation guide — the 'how' for a single task."""
    type: ArticleType = ArticleType.PROCEDURE
    task_id: int = Field(..., description="The task this procedure implements")
    objective: str = Field(..., description="What this task needs to achieve, 1-2 sentences")
    approach: str = Field(..., description="How to accomplish it, step-by-step methodology")
    verification: str = Field(..., description="How to confirm the task is complete and correct")


# ── Union type for dispatch ────────────────────────────────────

Article = BaseArticle | ProcessArticle | PlanArticle | HelpArticle | ResearchNoteArticle | NoteArticle | MissionArticle | ProcedureArticle


# ── Template definitions (what the AI uses to generate articles) ─

_AI_LAYER_BASE = ["id","title","slug","type","created_at","updated_at","reviewed_at","next_review_at","stability","sensitivity_label","confidence","keywords","summary","related","provenance","ai_notes","retrieval_count","link_count","last_accessed","lifecycle","superseded_by","doc_type","review_interval_days","version","history"]

TEMPLATES = {
    ArticleType.BASE: {
        "description": "Factoid / Wikipedia-style concept. ~5 paragraphs.",
        "ai_layer_fields": _AI_LAYER_BASE,
        "human_fields": ["content"],
        "prompt": "Write a concise, factual article (~5 paragraphs). No fluff. Start with a 1-sentence definition, then explain. End with why it matters.",
    },
    ArticleType.PROCESS: {
        "description": "Step-by-step procedure. Backup for rarely-used skills.",
        "ai_layer_fields": _AI_LAYER_BASE,
        "human_fields": ["steps","outcome","prerequisites"],
        "prompt": "Write step-by-step instructions. Each step must be an imperative command. End with an outcome statement. List prerequisites if any.",
    },
    ArticleType.PLAN: {
        "description": "Planning document for a goal.",
        "ai_layer_fields": _AI_LAYER_BASE,
        "human_fields": ["goal","phases","milestones","risks"],
        "prompt": "Write a planning document. State the goal first. List phases, milestones, and risks. Be specific, not aspirational.",
    },
    ArticleType.HELP: {
        "description": "Explains how a part of a project works.",
        "ai_layer_fields": _AI_LAYER_BASE + ["project","component"],
        "human_fields": ["explanation","examples"],
        "prompt": "Explain how a specific component of a project works. Name the project and component. ~5 paragraphs. Include examples if helpful.",
    },
    ArticleType.RESEARCH_NOTE: {
        "description": "Key notes for larger research — feeds into a base article.",
        "ai_layer_fields": _AI_LAYER_BASE + ["topic"],
        "human_fields": ["key_notes","open_questions","sources","target_base_slug"],
        "prompt": "Extract key research notes. Use bullet points. List open questions and sources. Note if this feeds into an existing base article.",
    },
    ArticleType.NOTE: {
        "description": "Temporary note — may relate to future work.",
        "ai_layer_fields": _AI_LAYER_BASE,
        "human_fields": ["content","related_project","actionable"],
        "prompt": "Write a brief note. ~5 paragraphs max. Flag if actionable. Note any related project. Keep it simple — this is temporary.",
    },
    ArticleType.MISSION: {
        "description": "Project building block — how a project will work.",
        "ai_layer_fields": _AI_LAYER_BASE + ["project"],
        "human_fields": ["purpose","architecture","dependencies","success_criteria"],
        "prompt": "Describe a project mission. State its purpose. Explain the architecture (~5 paragraphs). List dependencies and success criteria.",
    },
    ArticleType.PROCEDURE: {
        "description": "Task-specific implementation guide — the 'how' for a single task.",
        "ai_layer_fields": _AI_LAYER_BASE + ["task_id"],
        "human_fields": ["objective","approach","verification"],
        "prompt": "Write a task implementation guide. State the objective clearly. Describe the approach step by step. Specify how to verify completion.",
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
    ArticleType.PROCEDURE: ProcedureArticle,
}

def get_class(article_type: ArticleType | str) -> type:
    if isinstance(article_type, str):
        article_type = ArticleType(article_type)
    return ARTICLE_CLASSES[article_type]

def _serialize_provenance(p_list: List) -> List[dict]:
    """Serialize provenance to yaml-safe dicts."""
    out = []
    for p in p_list:
        if isinstance(p, dict):
            out.append(p)
        elif hasattr(p, 'model_dump'):
            out.append(p.model_dump(mode='json'))
        else:
            out.append(p)
    return out

def _serialize_related(r_list: List) -> List[dict]:
    """Serialize related edges to yaml-safe dicts."""
    out = []
    for r in r_list:
        if isinstance(r, dict):
            out.append(r)
        elif isinstance(r, str):
            out.append({"slug": r, "type": "see-also"})
        elif hasattr(r, 'model_dump'):
            out.append(r.model_dump(mode='json'))
        else:
            out.append(r)
    return out

def article_to_markdown(article) -> str:
    """Serialize any article to OKF markdown (YAML frontmatter + body)."""
    import yaml
    data = article.model_dump(mode='json')
    fm = {k: v for k, v in data.items() if v is not None}

    # Serialize sub-models
    if 'provenance' in fm:
        fm['provenance'] = _serialize_provenance(fm['provenance'])
    if 'related' in fm:
        fm['related'] = _serialize_related(fm['related'])
    if 'history' in fm and isinstance(fm.get('history'), list):
        fm['history'] = [
            h.model_dump(mode='json') if hasattr(h, 'model_dump') else h
            for h in fm['history']
        ]

    body_fields = TEMPLATES[article.type]["human_fields"]
    body = {}
    for k in body_fields:
        if k in fm:
            body[k] = fm.pop(k)
    # Add Obsidian tags for graph coloring
    fm['tags'] = [f'type/{article.type.value}']
    if fm.get('doc_type'):
        fm['tags'].append(f'doc/{fm["doc_type"]}')
    if fm.get('lifecycle') and fm['lifecycle'] != 'current':
        fm['tags'].append(f'lifecycle/{fm["lifecycle"]}')
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
    body_str = _format_body(body, article.type)
    # Append wikilinks section for Obsidian graph view
    related = fm.get('related', [])
    if related:
        slugs = []
        for r in related:
            s = r.get('slug', r) if isinstance(r, dict) else r
            slugs.append(s)
        wikilinks = ' '.join(f'[[{s}]]' for s in slugs)
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
