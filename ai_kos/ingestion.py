"""AI-KOS ingestion — parse any file, extract text, prepare for AI simplification.

Handles: .md, .txt, .pdf (via Docling), .docx (via Docling), .py/.js/etc (code)
Output: raw text + detected type + suggested template for AI processing.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ai-kos.ingest")

# File-type dispatch
_TEXT_EXTS = {'.md', '.txt', '.rst', '.org', '.log', '.jsonl'}
_CODE_EXTS = {'.py', '.js', '.ts', '.rs', '.go', '.java', '.cpp', '.c', '.h', '.sh', '.bash', '.yaml', '.yml', '.toml', '.json'}
_PDF_EXTS = {'.pdf'}
_DOCX_EXTS = {'.docx', '.doc'}
_OTHER_EXTS = {'.csv', '.html', '.xml', '.tex'}


def _read_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _read_pdf(filepath: str) -> str:
    """Extract text from PDF. Tries pymupdf, Docling, PyPDF2, then pdftotext."""
    # Try pymupdf (fast, reliable, handles most PDFs)
    try:
        import fitz
        doc = fitz.open(filepath)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return '\n\n'.join(pages)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"pymupdf failed: {e}")

    # Try Docling (best quality, preserves layout)
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(filepath)
        return result.document.export_to_markdown()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Docling failed: {e}")

    # Try PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        return '\n\n'.join(page.extract_text() or '' for page in reader.pages)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")

    # Fallback to pdftotext
    import subprocess
    try:
        result = subprocess.run(['pdftotext', filepath, '-'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass

    return f"[Could not extract text from PDF: {filepath}]"


def _read_docx(filepath: str) -> str:
    """Extract text from DOCX. Tries Docling first, then python-docx."""
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(filepath)
        return result.document.export_to_markdown()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Docling failed for DOCX: {e}")

    try:
        from docx import Document
        doc = Document(filepath)
        return '\n\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"python-docx failed: {e}")

    return f"[Could not extract text from DOCX: {filepath}]"


def _detect_article_type(content: str, filename: str) -> str:
    """Heuristic: guess the best article type based on content patterns."""
    lower = content.lower()
    fname = filename.lower()

    # Step-by-step patterns → process
    step_indicators = ['step 1', 'first,', '1.', '## steps', 'procedure', 'how to', 'instructions']
    if sum(1 for ind in step_indicators if ind in lower) >= 2:
        return "process"

    # Research patterns → research-note
    research_indicators = ['research', 'findings', 'methodology', 'literature', 'study', 'paper', 'experiment', 'abstract']
    if sum(1 for ind in research_indicators if ind in lower) >= 2:
        return "research-note"

    # Plan patterns → plan
    plan_indicators = ['milestone', 'timeline', 'phase', 'roadmap', 'goal:', 'objective', 'deliverable']
    if sum(1 for ind in plan_indicators if ind in lower) >= 2:
        return "plan"

    # Project/mission patterns → mission
    mission_indicators = ['architecture', 'deployment', 'stack', 'pipeline', 'service', 'api', 'database']
    if sum(1 for ind in mission_indicators if ind in lower) >= 3:
        return "mission"

    # Help/how-to patterns → help
    help_indicators = ['helps', 'guide', 'tutorial', 'reference', 'api docs', 'usage']
    if sum(1 for ind in help_indicators if ind in lower) >= 2:
        return "help"

    # Default: base article (factoid)
    return "base"


def extract(filepath: str) -> dict:
    """Extract text from any file. Returns structured dict for AI processing."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    ext = path.suffix.lower()
    filename = path.name

    # Read based on type
    if ext in _TEXT_EXTS:
        raw = _read_text(filepath)
        source_format = "text"
    elif ext in _CODE_EXTS:
        raw = _read_text(filepath)
        source_format = "code"
    elif ext in _PDF_EXTS:
        raw = _read_pdf(filepath)
        source_format = "pdf"
    elif ext in _DOCX_EXTS:
        raw = _read_docx(filepath)
        source_format = "docx"
    else:
        # Try reading as text, fallback
        try:
            raw = _read_text(filepath)
            source_format = "text"
        except Exception:
            return {"error": f"Unsupported file type: {ext}"}

    if not raw.strip():
        return {"error": "Empty file"}

    # Estimate token count (rough: 4 chars/token)
    token_est = len(raw) // 4

    # Detect suggested article type
    suggested_type = _detect_article_type(raw, filename)

    # Generate a slug from filename
    slug = filename.rsplit('.', 1)[0].lower().replace(' ', '-').replace('_', '-')

    return {
        "filepath": filepath,
        "filename": filename,
        "slug": slug,
        "source_format": source_format,
        "suggested_type": suggested_type,
        "token_estimate": token_est,
        "raw_content": raw,
    }
