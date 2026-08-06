"""AI-KOS citation extraction — extract DOI, title, authors from PDF metadata and Crossref API.

Uses pymupdf for PDF metadata extraction and the Crossref REST API for structured
citation lookup from DOIs. Falls back to extracting from first-page text.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("ai-kos.citation")


@dataclass
class Citation:
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    source: str = "unknown"  # "pdf_metadata", "first_page", "crossref", "manual"

    def to_dict(self) -> dict:
        return {
            "doi": self.doi,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "source": self.source,
        }

    def author_year_key(self) -> str:
        """Generate an author-year citation key: 'Conti2022' or 'Unknown2024'."""
        if self.authors and self.year:
            surname = self.authors[0].split()[-1] if self.authors else "Unknown"
            return f"{surname}{self.year}"
        if self.year:
            return f"Unknown{self.year}"
        return "Unknown"


def _extract_doi_from_text(text: str) -> Optional[str]:
    """Find a DOI in text using the standard pattern."""
    match = re.search(r'\b(10\.\d{4,}/[^\s]+)\b', text)
    return match.group(1).rstrip('.') if match else None


def _extract_arxiv_id(text: str) -> Optional[str]:
    """Find an arXiv ID in text, stripping version suffix for Crossref lookup."""
    match = re.search(r'arxiv:(\d{4}\.\d{4,})(?:v\d+)?', text, re.IGNORECASE)
    return match.group(1) if match else None


def extract_from_pdf(filepath: str) -> Citation:
    """Extract citation metadata from a PDF file.

    Tries in order: pymupdf metadata → first page text → Crossref lookup.
    """
    cit = Citation()

    # 1. Try pymupdf metadata
    try:
        import fitz
        doc = fitz.open(filepath)
        meta = doc.metadata
        doc.close()

        if meta.get('title'):
            cit.title = meta['title'].strip()
            cit.source = "pdf_metadata"
        if meta.get('author'):
            cit.authors = [a.strip() for a in meta['author'].split(';') if a.strip()]
    except Exception as e:
        logger.debug(f"pymupdf metadata failed: {e}")

    # 2. Try first page text for DOI
    try:
        import fitz
        doc = fitz.open(filepath)
        first_page = doc[0].get_text()
        doc.close()

        doi = _extract_doi_from_text(first_page)
        if doi:
            # Strip trailing version suffixes from arXiv DOIs
            doi = re.sub(r'v\d+$', '', doi)
            cit.doi = doi
            cit.source = "first_page"

        arxiv_id = _extract_arxiv_id(first_page)
        if arxiv_id and not cit.doi:
            cit.doi = f"10.48550/arXiv.{arxiv_id}"
            cit.source = "first_page"
    except Exception as e:
        logger.debug(f"First page extraction failed: {e}")

    # 3. If no title/authors, try extracting from first page pattern
    if not cit.title or not cit.authors:
        try:
            import fitz
            doc = fitz.open(filepath)
            first_page = doc[0].get_text()
            doc.close()

            # Try to find title in first 500 chars (typically the paper title)
            lines = first_page.split('\n')
            for i, line in enumerate(lines[:20]):
                stripped = line.strip()
                # Skip short lines, headers, DOI lines
                if len(stripped) > 30 and not stripped.startswith('http') and not stripped.startswith('DOI'):
                    if not cit.title:
                        cit.title = stripped
                        break
        except Exception:
            pass

    return cit


def lookup_crossref(doi: str) -> Citation:
    """Look up citation metadata from Crossref API using a DOI."""
    import json
    try:
        from urllib.request import urlopen, Request
        url = f"https://api.crossref.org/works/{doi}"
        req = Request(url, headers={"User-Agent": "AI-KOS/1.7 (mailto:kruzzzy@github)"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        msg = data.get("message", {})

        cit = Citation(doi=doi, source="crossref")
        cit.title = msg.get("title", [None])[0]
        cit.journal = msg.get("container-title", [None])[0] if msg.get("container-title") else None

        authors = msg.get("author", [])
        cit.authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors]

        published = msg.get("published-print", {}) or msg.get("published-online", {}) or msg.get("created", {})
        date_parts = published.get("date-parts", [[None]])[0]
        cit.year = date_parts[0] if date_parts else None

        return cit
    except Exception as e:
        logger.warning(f"Crossref lookup failed for {doi}: {e}")
        return Citation(doi=doi, source="crossref_error")


def extract_citation(filepath: str) -> Citation:
    """Full citation extraction: PDF metadata → first page → Crossref (if DOI found)."""
    cit = extract_from_pdf(filepath)

    # If we found a DOI, try Crossref for richer metadata
    if cit.doi and (not cit.title or not cit.authors or not cit.year):
        xref = lookup_crossref(cit.doi)
        if xref.source == "crossref":
            cit.title = cit.title or xref.title
            cit.authors = cit.authors or xref.authors
            cit.year = cit.year or xref.year
            cit.journal = cit.journal or xref.journal

    return cit
