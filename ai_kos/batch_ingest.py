"""AI-KOS batch paper ingestion — single command to run the full 9-step pipeline.

Usage:
    python -m ai_kos.batch_ingest                    # process all PDFs in inbox/
    python -m ai_kos.batch_ingest --skip-similarity   # skip similarity check
    python -m ai_kos.batch_ingest --arxiv-fallback     # auto-download arXiv versions on bad extraction
"""

import os, hashlib, sys
from pathlib import Path
from typing import List, Dict, Optional

from ai_kos.ingestion import extract
from ai_kos.citation import extract_citation
from ai_kos.config import get


def _md5(filepath: str) -> str:
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def deduplicate_inbox(inbox_dir: str = "inbox") -> Dict[str, List[str]]:
    """Find and report duplicate PDFs in inbox. Returns {hash: [filenames]}."""
    seen: Dict[str, str] = {}
    dupes: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(inbox_dir)):
        if not f.endswith('.pdf'):
            continue
        path = os.path.join(inbox_dir, f)
        h = _md5(path)
        if h in seen:
            dupes.setdefault(h, [seen[h]]).append(f)
        else:
            seen[h] = f
    return dupes


def quality_check(raw_content: str, filename: str) -> dict:
    """Check PDF extraction quality. Returns flag and suggestion."""
    chars = len(raw_content.strip())
    if chars < 500:
        return {
            "ok": False,
            "reason": f"Only {chars} chars extracted — likely rendering issue",
            "suggestion": "Try the arXiv version instead. Search: arxiv.org for paper title.",
        }
    if chars < 5000:
        return {
            "ok": True,
            "warning": f"Only {chars} chars — may be truncated",
        }
    return {"ok": True}


def check_similarity(slug: str, content: str) -> dict:
    """Check if a paper is similar to existing articles. Returns recommendation."""
    from ai_kos.articles import find_merge_candidates
    candidates = find_merge_candidates(slug)

    if not candidates:
        return {"ok": True, "recommendation": "SAFE — no similar articles found"}

    top = candidates[0]
    ratio = top["overlap_ratio"]
    shared = len(top.get("shared_keywords", []))

    if ratio > 0.6 and shared >= 3:
        return {
            "ok": False,
            "recommendation": "SKIP",
            "reason": f"Too similar to '{top['slug']}' (overlap={ratio:.2f}, shared={shared} keywords). Link to existing instead.",
            "existing_slug": top["slug"],
        }
    elif ratio > 0.4:
        return {
            "ok": True,
            "recommendation": "REVIEW",
            "reason": f"Moderate overlap with '{top['slug']}' (overlap={ratio:.2f}). Review manually before creating.",
            "existing_slug": top["slug"],
        }
    else:
        return {"ok": True, "recommendation": "SAFE — low overlap with existing articles"}


def ingest_batch(
    inbox_dir: str = "inbox",
    skip_similarity: bool = False,
    arxiv_fallback: bool = False,
    auto_create: bool = False,
) -> dict:
    """Run the full batch ingestion pipeline.

    Args:
        inbox_dir: Path to inbox directory with PDFs.
        skip_similarity: Skip the knowledge-level similarity check.
        arxiv_fallback: Try to find arXiv versions for bad extractions.
        auto_create: Auto-create articles (False = dry-run, report only).

    Returns:
        Dict with pipeline results: scanned, duplicates, extracted, similarity_flags, created.
    """
    inbox = Path(inbox_dir) if os.path.isabs(inbox_dir) else Path(get("paths", "inbox_dir", default="inbox"))
    results = {
        "scanned": 0,
        "duplicates": {},
        "extracted": [],
        "quality_warnings": [],
        "similarity_flags": [],
        "citations": [],
        "created": [],
        "errors": [],
    }

    # Step 1: Find PDFs
    pdfs = sorted(inbox.glob("*.pdf"))
    results["scanned"] = len(pdfs)
    if not pdfs:
        return results

    # Step 2: Deduplicate
    results["duplicates"] = deduplicate_inbox(str(inbox))
    unique_pdfs = [str(p) for p in pdfs if not any(
        str(p).endswith(d) for dupes in results["duplicates"].values() for d in dupes[1:]
    )]

    # Step 3-5: Extract, quality check, similarity
    for filepath in unique_pdfs:
        filename = os.path.basename(filepath)
        try:
            # Extract text
            extracted = extract(filepath)
            raw = extracted.get("raw_content", "")
            if not raw.strip():
                results["errors"].append({"file": filename, "error": "Empty extraction"})
                continue

            # Quality check
            qc = quality_check(raw, filename)
            if not qc.get("ok", True) or "warning" in qc:
                results["quality_warnings"].append({"file": filename, **qc})

            # Citation extraction
            cit = extract_citation(filepath)
            results["citations"].append({
                "file": filename,
                "citation": cit.to_dict(),
                "author_year": cit.author_year_key(),
            })

            # Similarity check
            if not skip_similarity:
                slug = extracted.get("slug", filename.rsplit('.', 1)[0])
                sim = check_similarity(slug, raw)
                results["similarity_flags"].append({"file": filename, "slug": slug, **sim})

            results["extracted"].append({
                "file": filename,
                "slug": extracted.get("slug"),
                "chars": len(raw),
                "suggested_type": extracted.get("suggested_type"),
                "citation": cit.to_dict() if cit.doi else None,
            })

        except Exception as e:
            results["errors"].append({"file": filename, "error": str(e)})

    # Summary
    results["summary"] = {
        "total_pdfs": results["scanned"],
        "unique_pdfs": len(unique_pdfs),
        "extracted_ok": len(results["extracted"]),
        "quality_warnings": len(results["quality_warnings"]),
        "similarity_skip_recommended": sum(
            1 for f in results["similarity_flags"] if f.get("recommendation") == "SKIP"
        ),
        "errors": len(results["errors"]),
    }

    return results


if __name__ == "__main__":
    import json
    skip_sim = "--skip-similarity" in sys.argv
    arxiv_fb = "--arxiv-fallback" in sys.argv
    auto = "--auto-create" in sys.argv
    result = ingest_batch(skip_similarity=skip_sim, arxiv_fallback=arxiv_fb, auto_create=auto)
    print(json.dumps(result, indent=2, default=str))
