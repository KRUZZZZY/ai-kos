"""AI-KOS Deep Research Engine — multi-step autonomous research pipeline.

Based on architectural patterns from Google Gemini Deep Research, OpenAI Deep Research,
Perplexity Sonar, and Stanford STORM.

Flow:
  1. PLAN: decompose question into sub-questions + search strategy
  2. SEARCH: web search each sub-question, extract top sources
  3. CROSS-REFERENCE: check AI-KOS knowledge base for existing knowledge
  4. SYNTHESIZE: reconcile findings, resolve contradictions, structure report
  5. PERSIST: save as research-note + base articles in AI-KOS

Designed to work with Hermes's web_search/web_extract tools and AI-KOS's search/articles.
"""

import json
import re
import uuid
import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("ai-kos.deep-research")


@dataclass
class ResearchPlan:
    """A structured research plan with sub-questions and search strategy."""
    id: str
    question: str
    sub_questions: List[str]           # 3-5 decomposed sub-questions
    search_queries: List[str]          # specific search queries per sub-question
    perspectives: List[str]            # what angles to investigate
    status: str = "planned"            # planned | running | completed | failed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SourceFinding:
    """A single finding from a web source."""
    sub_question_idx: int
    source_url: str
    source_title: str
    key_claim: str                     # the main finding/claim from this source
    evidence: str                      # supporting evidence or quote
    confidence: str = "medium"         # high | medium | low


@dataclass  
class CrossReference:
    """Cross-reference result between web findings and AI-KOS knowledge."""
    finding: str
    existing_article: Optional[str]    # AI-KOS article slug if found
    relationship: str                  # confirms | contradicts | extends | new
    notes: str = ""


@dataclass
class ResearchResult:
    """Complete research result ready for persistence."""
    id: str
    plan_id: str
    question: str
    sub_questions: List[str]
    findings: List[Dict[str, Any]]
    cross_references: List[Dict[str, Any]]
    synthesis: str                     # final synthesized report
    knowledge_gaps: List[str]          # things we still don't know
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def plan_research(question: str) -> ResearchPlan:
    """Decompose a research question into sub-questions and search queries.
    
    Uses STORM-style perspective generation: creates 3-5 angles to investigate.
    Returns a ResearchPlan that can be reviewed before execution.
    """
    plan_id = str(uuid.uuid4())[:8]

    # Generate sub-questions by analyzing the question's dimensions
    sub_questions = _decompose_question(question)
    search_queries = _generate_queries(sub_questions)
    perspectives = _generate_perspectives(question)

    return ResearchPlan(
        id=plan_id,
        question=question,
        sub_questions=sub_questions,
        search_queries=search_queries,
        perspectives=perspectives,
    )


def _decompose_question(question: str) -> List[str]:
    """Break a question into 3-5 focused sub-questions."""
    # The actual decomposition is done by the LLM (Hermes).
    # This returns a template that Hermes fills in via the MCP tool.
    return [
        f"What are the core concepts and definitions related to: {question[:80]}?",
        f"What are the current approaches, tools, or methods for: {question[:80]}?",
        f"What are the key challenges, limitations, or trade-offs in: {question[:80]}?",
        f"What evidence, data, or benchmarks exist for: {question[:80]}?",
        f"What are the emerging trends or future directions in: {question[:80]}?",
    ]


def _generate_queries(sub_questions: List[str]) -> List[str]:
    """Generate specific search queries from sub-questions."""
    queries = []
    for sq in sub_questions:
        # Strip the question prefix, use as search query
        q = sq.split(": ", 1)[-1] if ": " in sq else sq
        queries.append(q[:150])
    return queries


def _generate_perspectives(question: str) -> List[str]:
    """STORM-style: generate diverse perspectives to investigate."""
    return [
        f"Technical/Implementation: How does it work? What are the mechanisms?",
        f"Comparative: How does it compare to alternatives? What are the trade-offs?",
        f"Practical/Applied: What are real-world use cases? What works in practice?",
        f"Critical/Limitations: What are the weaknesses, risks, or open problems?",
        f"Future/Evolution: Where is this heading? What's next?",
    ]


def spill_if_large(text: str, name: str, max_chars: int = 4000,
                   spill_dir: Optional[str] = None,
                   session_id: str = "deep-research") -> Any:
    """Spill oversized raw extraction text to the spill store.

    Returns the text unchanged when ``len(text) <= max_chars``; otherwise
    returns a :class:`ai_kos.spill.SpillRef` whose ``locator`` replaces the
    full text in extraction results. Additive — never truncates existing
    behavior for small text.
    """
    from ai_kos.spill import apply_spill_policy
    return apply_spill_policy(text, name, max_chars=max_chars,
                              spill_dir=spill_dir, session_id=session_id)


def structure_findings(raw_findings: List[Dict[str, Any]]) -> List[SourceFinding]:
    """Structure raw search results into typed findings.

    Oversized raw extraction text (>4000 chars) is spilled to a session-scoped
    file and the locator is kept in the result dict in place of the full text.
    """
    structured = []
    for f in raw_findings:
        content = f.get("content", "")
        evidence = f.get("evidence", content[:300])
        if len(content) > 4000:
            ref = spill_if_large(content, f"extract-{f.get('sub_question_idx', 0)}")
            f["content"] = ref.locator  # locator kept in place of the full text
        structured.append(SourceFinding(
            sub_question_idx=f.get("sub_question_idx", 0),
            source_url=f.get("url", ""),
            source_title=f.get("title", ""),
            key_claim=f.get("key_claim", f.get("description", "")),
            evidence=evidence,
            confidence=f.get("confidence", "medium"),
        ))
    return structured


def cross_reference_with_knowledge(findings: List[SourceFinding]) -> List[CrossReference]:
    """Cross-reference web findings against AI-KOS knowledge base."""
    from ai_kos.search import search
    refs = []

    for f in findings:
        # Search AI-KOS for related articles
        results = search(f.key_claim, top_k=3)
        if results and results[0]["score"] > 1.0:
            # Found relevant existing knowledge
            top = results[0]
            refs.append(CrossReference(
                finding=f.key_claim[:100],
                existing_article=top["slug"],
                relationship=_classify_relationship(f.key_claim, top["snippet"]),
                notes=f"AI-KOS match: {top['title']} (score={top['score']:.2f})",
            ))
        else:
            # New knowledge not in AI-KOS
            refs.append(CrossReference(
                finding=f.key_claim[:100],
                existing_article=None,
                relationship="new",
                notes="No existing AI-KOS article found — knowledge gap.",
            ))

    return refs


def _classify_relationship(claim: str, existing: str) -> str:
    """Simple heuristic: does the claim confirm, contradict, or extend existing knowledge?"""
    claim_lower = claim.lower()
    existing_lower = existing.lower()
    # Check for contradiction markers
    contradict_words = ["however", "but", "contrary", "unlike", "differs", "disagree"]
    if any(w in claim_lower for w in contradict_words):
        return "contradicts"
    # Check if it extends (builds on)
    extend_words = ["additionally", "furthermore", "moreover", "extends", "builds on", "also"]
    if any(w in claim_lower for w in extend_words):
        return "extends"
    return "confirms"


def synthesize_report(result: ResearchResult) -> str:
    """Synthesize all findings into a structured markdown report."""
    lines = [
        f"# Deep Research: {result.question}",
        f"",
        f"*Generated: {result.created_at}*",
        f"",
        f"## Research Questions",
    ]
    for i, sq in enumerate(result.sub_questions, 1):
        lines.append(f"{i}. {sq}")
    lines.append("")

    lines.append("## Key Findings")
    for i, f in enumerate(result.findings, 1):
        lines.append(f"### Finding {i}: {f.get('source_title', 'Unknown Source')}")
        lines.append(f"**Claim:** {f.get('key_claim', '')}")
        lines.append(f"**Source:** {f.get('source_url', '')}")
        lines.append(f"**Confidence:** {f.get('confidence', 'medium')}")
        lines.append("")

    lines.append("## Cross-Reference with AI-KOS Knowledge Base")
    for cr in result.cross_references:
        icon = {"confirms": "✅", "contradicts": "⚠️", "extends": "➕", "new": "🆕"}.get(cr.get("relationship", ""), "❓")
        lines.append(f"- {icon} **{cr.get('relationship', '').upper()}**: {cr.get('finding', '')[:100]}")
        if cr.get("existing_article"):
            lines.append(f"  - Existing article: [[{cr['existing_article']}]]")
        lines.append(f"  - {cr.get('notes', '')}")
    lines.append("")

    lines.append("## Knowledge Gaps")
    for gap in result.knowledge_gaps:
        lines.append(f"- {gap}")
    if not result.knowledge_gaps:
        lines.append("- No significant gaps identified.")
    lines.append("")

    if result.synthesis:
        lines.append("## Synthesis")
        lines.append(result.synthesis)

    return "\n".join(lines)


def _smart_truncate(text: str, max_len: int) -> str:
    """Truncate at last word boundary before max_len."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rstrip()
    # Try to break at last space
    last_space = cut.rfind(' ')
    if last_space > max_len // 2:
        return cut[:last_space]
    return cut


def persist_research(result: ResearchResult, knowledge_dir: str = "knowledge") -> Dict[str, str]:
    """Save research findings as AI-KOS articles: one research-note per sub-question, one base synthesis."""
    from ai_kos.articles import create_article

    created = {}
    today = date.today()

    # Create research-note for overall findings
    key_notes = []
    for f in result.findings[:10]:
        key_notes.append(f"{f.get('key_claim', '')} [{f.get('title', '')}]")

    gaps = result.knowledge_gaps if result.knowledge_gaps else ["No significant gaps identified"]

    # Generate a clean title
    clean_title = _smart_truncate(result.question, 80)

    slug = re.sub(r'[^a-z0-9\s-]', '', result.question.lower()).replace(" ", "-")[:50]
    slug = re.sub(r'-+', '-', slug).strip('-')

    # Extract a clean summary from synthesis (first non-heading, non-empty paragraph)
    summary_text = ""
    if result.synthesis:
        for line in result.synthesis.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                summary_text = stripped[:250]
                break
    if not summary_text:
        summary_text = f"Deep research findings on: {clean_title}"

    r = create_article("research-note", {
        "title": f"Research: {clean_title}",
        "slug": f"research-{slug}",
        "keywords": _extract_keywords(result.question)[:8],
        "summary": summary_text[:250],
        "provenance": [f.get("url", "") for f in result.findings[:5]],
        "stability": "volatile",
        "sensitivity_label": "internal",
        "topic": clean_title,
        "key_notes": key_notes,
        "open_questions": gaps,
        "sources": [f"{f.get('title', '')}: {f.get('url', '')}" for f in result.findings[:10]],
    })
    if r.get("status") == "created":
        created["research_note"] = r["slug"]

    # Create base synthesis article
    if result.synthesis:
        base_slug = slug[:45]
        r2 = create_article("base", {
            "title": clean_title,
            "slug": base_slug,
            "keywords": _extract_keywords(result.question)[:8],
            "summary": summary_text[:250],
            "provenance": ["deep-research-synthesis"],
            "stability": "moderate",
            "sensitivity_label": "internal",
            "content": result.synthesis,
        })
        if r2.get("status") == "created":
            created["base_article"] = r2["slug"]

    return created


def _extract_keywords(text: str) -> List[str]:
    """Extract likely keywords from text (simple heuristic)."""
    words = re.findall(r'[a-zA-Z]{4,}', text.lower())
    stop = {'this','that','with','from','have','been','were','they','their','about','which','what','when','where','over','into','such','other','only','also','very','just','some','each','both','more','most','many','and','using','the','are','was','not','all','can','has','had','its','but'}
    return list(dict.fromkeys(w for w in words if w not in stop))[:8]


def pmc_to_pdf(url: str) -> str:
    """Convert a PMC article URL to its PDF version for cleaner extraction.

    PMC HTML pages return nav-heavy boilerplate from web_extract.
    The PDF endpoint yields clean article text with none of that noise.
    Non-PMC URLs are returned unchanged.
    """
    match = re.match(r'(https?://www\.ncbi\.nlm\.nih\.gov/pmc/articles/PMC\d+)', url)
    if match:
        return f"{match.group(1)}/pdf/"
    return url
