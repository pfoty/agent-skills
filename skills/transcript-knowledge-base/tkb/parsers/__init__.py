"""Parser package.

Importing this package registers every built-in parser (their ``@register``
decorators run on import). Use :func:`parse_file` to dispatch by extension.
"""

from __future__ import annotations

import os

from .base import ParseError, RawTranscript, get_parser, supported_extensions

# Import for side effects: each module registers itself.
from . import text_parser  # noqa: F401
from . import json_parser  # noqa: F401
from . import caption_parser  # noqa: F401
from . import csv_parser  # noqa: F401
from . import docx_parser  # noqa: F401

__all__ = ["parse_file", "RawTranscript", "ParseError", "supported_extensions", "get_parser"]

# Binary formats read their own bytes; we must not slurp them as UTF-8 text.
_BINARY_EXTS = {".docx"}


def parse_file(path: str) -> RawTranscript:
    """Read and parse a transcript file based on its extension."""
    ext = os.path.splitext(path)[1].lower()
    parser = get_parser(ext)
    if parser is None:
        raise ParseError(f"no parser registered for extension {ext!r}")
    if ext in _BINARY_EXTS:
        return parser(path, "")
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    return parser(path, content)
