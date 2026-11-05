"""Parser contract and registry.

Each parser converts one transcript format into a format-agnostic
:class:`RawTranscript` (metadata + ordered raw turns). ``prepare`` then renders
that into a citation-tagged brief for extraction.

Keeping parsing separate from everything downstream means a new format only needs
a small parser; the scan/brief/merge logic is shared and tested once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class RawTurn:
    """A speaker turn as read from the source, before canonicalization."""

    speaker: Optional[str]
    text: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@dataclass
class RawTranscript:
    """Format-agnostic parse result."""

    turns: list[RawTurn]
    title: Optional[str] = None
    conversation_date: Optional[str] = None
    participants: list[str] = field(default_factory=list)
    language: Optional[str] = None
    source_system: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class ParseError(Exception):
    """Raised when a file cannot be parsed into a usable transcript."""


# Registry: extension -> parse function. Populated by register().
_REGISTRY: dict[str, Callable[[str, str], RawTranscript]] = {}


def register(*extensions: str):
    """Decorator registering a parser for one or more extensions."""

    def deco(fn: Callable[[str, str], RawTranscript]):
        for ext in extensions:
            _REGISTRY[ext.lower()] = fn
        return fn

    return deco


def get_parser(extension: str) -> Optional[Callable[[str, str], RawTranscript]]:
    return _REGISTRY.get(extension.lower())


def supported_extensions() -> frozenset[str]:
    return frozenset(_REGISTRY)
