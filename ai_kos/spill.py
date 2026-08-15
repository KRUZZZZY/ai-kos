"""AI-KOS spill — persist oversized tool output to session-scoped files.

Mirrors DeepSeek Harness' spill capability: oversized tool output leaves the
model context; a bounded preview + branded retrieval locator stays inline.
The full text is retrieved later via the locator.

Locator format: ``spill:<session_id>/<filename>``.

Integration: ``deep_research`` extraction paths call :func:`spill_if_large` so
raw text over the budget becomes a :class:`SpillRef` instead of context.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from ai_kos.config import get

logger = logging.getLogger("ai-kos.spill")

SPILL_LOCATOR_PREFIX = "spill:"


class SpillError(Exception):
    """Base error for spill storage failures."""


@dataclass
class SpillRef:
    """Reference to spilled text: preview + retrieval locator."""

    locator: str
    preview: str
    path: str
    size_bytes: int
    truncated: bool


@dataclass
class SpillPolicy:
    """Post-execution spill policy: spill only when over budget."""

    max_chars: int = 4000
    name: str = "output"
    spill_dir: Optional[str] = None
    session_id: str = "default"
    preview_chars: int = 2000


def default_spill_dir() -> Path:
    """Default spill directory (config ``paths.spills_dir``, else datasets/spills)."""
    return Path(get("paths", "spills_dir", default="datasets/spills"))


def _sanitize(name: str) -> str:
    """Filesystem-safe name fragment."""
    return re.sub(r"[^a-zA-Z0-9._-]", "-", name)[:80] or "output"


def spill(
    text: str,
    name: str,
    spill_dir: Optional[str] = None,
    session_id: str = "default",
    preview_chars: int = 2000,
) -> SpillRef:
    """Persist ``text`` to a session-scoped file; return a preview + locator.

    Durable by construction: the file is written fully before the SpillRef
    exists (write-then-act — an interrupted spill yields no locator).
    """
    d = Path(spill_dir) if spill_dir else default_spill_dir()
    session_dir = d / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fname = f"{_sanitize(name)}-{ts}.txt"
    path = session_dir / fname
    path.write_text(text)
    size = path.stat().st_size
    truncated = len(text) > preview_chars
    if truncated:
        preview = text[:preview_chars] + f"… [truncated {len(text) - preview_chars} chars]"
    else:
        preview = text
    locator = f"{SPILL_LOCATOR_PREFIX}{session_id}/{fname}"
    logger.info("spilled %d chars to %s (%s)", size, path,
                "truncated preview" if truncated else "full preview")
    return SpillRef(locator=locator, preview=preview, path=str(path),
                    size_bytes=size, truncated=truncated)


def retrieve(locator: str, spill_dir: Optional[str] = None) -> str:
    """Return the full spilled text for a ``spill:`` locator."""
    if not locator or not locator.startswith(SPILL_LOCATOR_PREFIX):
        raise SpillError(f"invalid locator: {locator!r}")
    rel = locator[len(SPILL_LOCATOR_PREFIX):]
    d = Path(spill_dir) if spill_dir else default_spill_dir()
    base = d.resolve()
    p = (base / rel).resolve()
    if not p.is_relative_to(base):
        raise SpillError(f"locator escapes spill dir: {locator!r}")
    if not p.exists():
        raise SpillError(f"spilled text not found: {locator!r}")
    return p.read_text()


def apply_spill_policy(text: str, name: str, max_chars: int = 4000, **kw) -> Union[SpillRef, str]:
    """Apply a spill policy: small text passes through, oversized text spills.

    Returns a :class:`SpillRef` when ``len(text) > max_chars``, else the text
    unchanged.
    """
    if len(text) <= max_chars:
        return text
    return spill(text, name, **kw)


def spill_if_large(
    text: str,
    name: str = "extraction",
    max_chars: int = 4000,
    spill_dir: Optional[str] = None,
    session_id: str = "default",
) -> Union[SpillRef, str]:
    """Convenience for extraction paths: spill only when over budget.

    Returns the unchanged string when small (callers keep existing behavior),
    or a :class:`SpillRef` with a bounded preview when oversized.
    """
    return apply_spill_policy(text, name, max_chars=max_chars,
                              spill_dir=spill_dir, session_id=session_id)
