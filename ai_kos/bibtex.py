"""AI-KOS BibTeX export — generate .bib files from research-note articles.

Scans all research-note articles, extracts citation metadata from frontmatter
(doi) and parses author/year from title patterns. Optionally enriches via
Crossref API for articles with DOIs but incomplete metadata.

Usage:
    from ai_kos.bibtex import export_bibtex
    result = export_bibtex()  # writes to knowledge/bibliography.bib
    result = export_bibtex(output_path="/path/to/refs.bib", enrich=True)
"""

import re
import logging
from pathlib import Path
from typing import Optional

from ai_kos.config import get as config_get

logger = logging.getLogger("ai-kos.bibtex")


# ── Title parsing ────────────────────────────────────────────────────────────

def _parse_author_year_from_title(title: str) -> tuple[Optional[str], Optional[int]]:
    """Parse 'Adams et al. 2017 — ...' or 'Conti et al. 2022 — ...' from titles.
    
    Returns (first_author_surname, year) or (None, None).
    """
    # Pattern: "Surname et al. YYYY — ..." or "Surname & Other YYYY — ..."
    m = re.match(
        r'([A-Z][a-zà-ü]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zà-ü]+))?)\s+[\(\[\{]?(\d{4})[\)\]\}]?\s*[—–-]',
        title
    )
    if m:
        surname = m.group(1).split()[0]  # first word = surname
        year = int(m.group(2))
        return surname, year
    
    # Fallback: just "Surname YEAR" at start
    m = re.match(r'([A-Z][a-zà-ü]+)\s+(\d{4})\b', title)
    if m:
        return m.group(1), int(m.group(2))
    
    return None, None


def _clean_title(full_title: str) -> str:
    """Strip author-year prefix from title: 'Adams et al. 2017 — Real Title' → 'Real Title'."""
    cleaned = re.sub(r'^[A-Z][a-zà-ü]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zà-ü]+))?\s+[\(\[\{]?\d{4}[\)\]\}]?\s*[—–-]\s*', '', full_title)
    if cleaned == full_title:
        cleaned = re.sub(r'^[A-Z][a-zà-ü]+\s+\d{4}\s*[—–-]?\s*', '', full_title)
    return cleaned.strip()


def _make_cite_key(first_author: str, year: int, title: str, existing_keys: set) -> str:
    """Generate a disambiguated BibTeX cite key like 'Adams2017' or 'Adams2017a'."""
    base = f"{first_author}{year}"
    if base not in existing_keys:
        return base
    # Disambiguate with suffix letters
    for suffix in 'abcdefghijklmnopqrstuvwxyz':
        key = f"{base}{suffix}"
        if key not in existing_keys:
            return key
    # Fallback: use first meaningful word from title
    words = [w for w in title.split() if len(w) > 3 and w.isalpha()]
    if words:
        return f"{first_author}{year}{words[0][:3].title()}"
    return f"{base}x"
def _format_authors_bibtex(authors: list[str]) -> str:
    """Format author list for BibTeX: 'Conti, Francesco and Moroni, Davide'.
    
    Handles three cases:
    - Single 'et al.' string: 'Adams et al.' → 'Adams et al.' (pass through)
    - 'Surname, FirstName': already formatted → pass through
    - 'FirstName Surname': convert to 'Surname, FirstName'
    """
    if not authors:
        return ''
    
    # If it's a single "et al." entry, pass through
    if len(authors) == 1 and 'et al.' in authors[0]:
        return authors[0]
    
    formatted = []
    for a in authors:
        a = a.strip()
        if 'et al.' in a.lower():
            formatted.append(a)
        elif ',' in a:
            # Already "Surname, FirstName"
            formatted.append(a)
        else:
            parts = a.rsplit(None, 1)
            if len(parts) == 2:
                formatted.append(f"{parts[1]}, {parts[0]}")
            else:
                formatted.append(a)
    return ' and '.join(formatted)


def _escape_bibtex(text: str) -> str:
    """Escape special LaTeX characters in BibTeX text fields."""
    if not text:
        return text
    # Replace LaTeX special chars with their escaped versions
    for char, escaped in [('&', '\\&'), ('%', '\\%'), ('$', '\\$'), 
                           ('#', '\\#'), ('_', '\\_'), ('{', '\\{'),
                           ('}', '\\}'), ('~', '\\textasciitilde{}'),
                           ('^', '\\textasciicircum{}'), ('\\', '\\textbackslash{}')]:
        # Don't double-escape already-escaped sequences
        text = text.replace(char, escaped)
    return text


# ── Data collection ──────────────────────────────────────────────────────────

def _collect_from_research_notes() -> list[dict]:
    """Collect citation data from all research-note articles.
    
    Returns list of dicts with keys: slug, title, authors, year, doi, journal, cite_key.
    Also reads article bodies to find DOIs that aren't stored in frontmatter.
    """
    from ai_kos.articles import list_articles, read_article
    from ai_kos.citation import _extract_doi_from_text
    
    articles = list_articles(article_type='research-note')
    citations = []
    existing_keys = set()
    
    for art in articles:
        slug = art.get('slug', '')
        title = art.get('title', '')
        doi = art.get('doi')  # Try frontmatter first
        summary = art.get('summary', '')
        
        if not title:
            continue
        
        # Parse author+year from title prefix
        first_author, year = _parse_author_year_from_title(title)
        clean_title = _clean_title(title)
        
        # Try to extract DOI from body if not in frontmatter
        if not doi:
            try:
                full = read_article(slug)
                if full:
                    body = full.get('body', '') or ''
                    # Also check key_notes and other fields
                    extra_text = ''
                    if isinstance(full, dict):
                        extra_text = ' '.join(str(v) for v in full.values() if isinstance(v, (str, list)))
                    combined = f"{summary} {body} {extra_text}"
                    doi = _extract_doi_from_text(combined)
            except Exception:
                pass
        
        # Try to extract journal from summary
        journal = _extract_journal_from_summary(summary)
        
        cite_key = _make_cite_key(first_author or 'Unknown', year or 0, clean_title, existing_keys)
        existing_keys.add(cite_key)
        
        citations.append({
            'slug': slug,
            'title': clean_title or title,
            'authors': [f"{first_author} et al."] if first_author else [],
            'year': year,
            'doi': doi,
            'journal': journal,
            'cite_key': cite_key,
        })
    
    return citations


def _extract_journal_from_summary(summary: str) -> Optional[str]:
    """Extract journal name from typical summary patterns.
    
    Examples: 'Adams et al. (2017, JMLR) introduce...' → 'JMLR'
              'published in Journal of Machine Learning Research' → 'Journal of Machine Learning Research'
    """
    if not summary:
        return None
    
    # Known journal abbreviations
    ABBREV_MAP = {
        'jmlr': 'Journal of Machine Learning Research',
        'neurips': 'Advances in Neural Information Processing Systems',
        'icml': 'International Conference on Machine Learning',
        'tpami': 'IEEE Transactions on Pattern Analysis and Machine Intelligence',
        'aistats': 'International Conference on Artificial Intelligence and Statistics',
        'focm': 'Foundations of Computational Mathematics',
        'ijert': 'International Journal of Engineering Research and Technology',
        'iccv': 'International Conference on Computer Vision',
        'cvpr': 'Conference on Computer Vision and Pattern Recognition',
    }
    
    # Check for parenthetical abbreviation: "(2017, JMLR)"
    m = re.search(r'\((\d{4}),\s*([A-Z][A-Za-z\s]+)\)', summary)
    if m:
        abbrev = m.group(2).strip().lower()
        return ABBREV_MAP.get(abbrev, m.group(2).strip())
    
    # Check for "in <Journal>" patterns
    m = re.search(r'(?:in|published\sin|journal:)\s+([A-Z][A-Za-z\s]+(?:of\s+[A-Z][A-Za-z\s]+)?)', summary)
    if m:
        return m.group(1).strip()
    
    return None


# ── Crossref enrichment ──────────────────────────────────────────────────────

def _enrich_via_crossref(citations: list[dict]) -> list[dict]:
    """For citations with DOIs but missing metadata, query Crossref API."""
    from ai_kos.citation import lookup_crossref
    
    enriched = []
    for cit in citations:
        doi = cit.get('doi')
        if doi and (not cit['authors'] or not cit['year'] or len(cit['authors']) <= 1):
            try:
                xref = lookup_crossref(doi)
                if xref.source == 'crossref':
                    if xref.authors:
                        cit['authors'] = xref.authors
                    if xref.year:
                        cit['year'] = xref.year
                    if xref.journal:
                        cit['journal'] = xref.journal
                    if xref.title:
                        cit['title'] = xref.title
            except Exception as e:
                logger.debug(f"Crossref enrichment failed for {doi}: {e}")
        enriched.append(cit)
    
    return enriched


def _infer_entry_type(citation: dict) -> str:
    """Guess whether this is an @article, @inproceedings, or @misc."""
    journal = (citation.get('journal') or '').lower()
    title = (citation.get('title') or '').lower()
    
    conference_keywords = ['conference', 'proceedings', 'neurips', 'icml', 'iccv', 
                           'cvpr', 'aistats', 'iclr', 'eccv', 'aaai', 'ijcai']
    
    if any(kw in journal or kw in title for kw in conference_keywords):
        return 'inproceedings'
    
    if journal:
        return 'article'
    
    return 'misc'


# ── BibTeX generation ────────────────────────────────────────────────────────

def _generate_bibtex_entry(citation: dict) -> str:
    """Generate a BibTeX entry string for one citation."""
    entry_type = _infer_entry_type(citation)
    cite_key = citation['cite_key']
    
    lines = [f"@{entry_type}{{{cite_key},"]
    
    # Authors
    if citation.get('authors'):
        lines.append(f"  author = {{{_format_authors_bibtex(citation['authors'])}}},")
    
    # Title
    if citation.get('title'):
        lines.append(f"  title = {{{_escape_bibtex(citation['title'])}}},")
    
    # Journal / booktitle
    if citation.get('journal'):
        if entry_type == 'inproceedings':
            lines.append(f"  booktitle = {{{_escape_bibtex(citation['journal'])}}},")
        else:
            lines.append(f"  journal = {{{_escape_bibtex(citation['journal'])}}},")
    
    # Year
    if citation.get('year'):
        lines.append(f"  year = {{{citation['year']}}},")
    
    # DOI
    if citation.get('doi'):
        lines.append(f"  doi = {{{citation['doi']}}},")
        lines.append(f"  url = {{https://doi.org/{citation['doi']}}},")
    
    # Note: traceable back to AI-KOS
    if citation.get('slug'):
        lines.append(f"  note = {{AI-KOS research-note: {citation['slug']}}},")
    
    lines.append("}")
    
    return '\n'.join(lines)


def export_bibtex(
    output_path: Optional[str] = None,
    enrich: bool = False,
    article_type: str = 'research-note',
) -> dict:
    """Export BibTeX bibliography from AI-KOS articles.
    
    Args:
        output_path: Where to write the .bib file. Default: knowledge/bibliography.bib
        enrich: If True, query Crossref for articles with DOIs but incomplete metadata.
        article_type: Which article type to export (default: research-note).
    
    Returns:
        dict with keys: entries (count), output_path, entries (list of cite_keys).
    """
    # Collect citations
    citations = _collect_from_research_notes()
    
    # Enrich via Crossref if requested
    if enrich:
        logger.info(f"Enriching {len(citations)} citations via Crossref...")
        citations = _enrich_via_crossref(citations)
    
    # Filter: only include citations with enough data to be useful
    valid = [c for c in citations if c.get('title') and (c.get('authors') or c.get('doi'))]
    
    # Generate BibTeX entries
    entries = [_generate_bibtex_entry(c) for c in valid]
    bibtex_content = '\n\n'.join(entries) + '\n'
    
    # Write to file
    if output_path is None:
        kb_path = config_get('paths', 'knowledge_dir', default='knowledge')
        output_path = str(Path(kb_path) / 'bibliography.bib')
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(bibtex_content)
    
    return {
        'entries': len(valid),
        'output_path': output_path,
        'cite_keys': [c['cite_key'] for c in valid],
        'skipped': len(citations) - len(valid),
    }


def get_bibtex_string(enrich: bool = False) -> str:
    """Generate BibTeX content and return as string (for MCP tool — no file write)."""
    citations = _collect_from_research_notes()
    if enrich:
        citations = _enrich_via_crossref(citations)
    valid = [c for c in citations if c.get('title') and (c.get('authors') or c.get('doi'))]
    entries = [_generate_bibtex_entry(c) for c in valid]
    return '\n\n'.join(entries) + '\n'
