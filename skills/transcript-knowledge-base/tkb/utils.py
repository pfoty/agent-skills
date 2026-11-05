"""Small shared helpers: hashing, timestamps, tokens, text normalization."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


def now_iso() -> str:
    """UTC timestamp in ISO-8601. Centralized so it can be monkeypatched in tests."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str, chunk_size: int = 65536) -> str:
    """Content hash of a file, used for change detection and source_file_id."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token). Good enough for chunk sizing."""
    return max(1, len(text) // 4)


_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """
    the a an and or but if then else for to of in on at by with from as is are was
    were be been being this that these those it its i you he she we they them me my
    our your their will would shall should can could may might must do does did have
    has had not no yes so just very really about into over under than too also okay ok
    """.split()
)


def keywords(text: str, limit: int = 12) -> list[str]:
    """Extract content keywords (lowercased, stopword-filtered, de-duplicated).

    Used both for topic labels and as the similarity signal for consolidation.
    Order-preserving so the output is deterministic.
    """
    seen: dict[str, None] = {}
    for word in _WORD_RE.findall(text.lower()):
        if len(word) <= 2 or word in _STOPWORDS:
            continue
        seen.setdefault(word, None)
        if len(seen) >= limit:
            break
    return list(seen.keys())


def jaccard(a: set[str], b: set[str]) -> float:
    """Set similarity in [0,1]. Used to cluster related knowledge objects."""
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# Reasonably permissive date matcher for owner/due-date inference.
_DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:,?\s+\d{4})?)\b",
        re.IGNORECASE,
    ),
]


def find_date(text: str) -> str | None:
    """Return the first date-like string found, or None."""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None
