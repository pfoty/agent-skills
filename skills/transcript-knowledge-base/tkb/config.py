"""Configuration loading.

Config is a small dataclass with sane defaults, overlayable from a YAML or JSON
file or constructed directly in tests. YAML is optional (PyYAML); JSON always
works.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from typing import Any, Optional

# Transcript file types we can parse. .docx is the primary Copilot/Teams export.
DEFAULT_SUPPORTED_EXTENSIONS = (".docx", ".txt", ".md", ".json", ".vtt", ".srt", ".csv")


@dataclass
class Config:
    """Runtime configuration for the knowledge index."""

    folder_path: Optional[str] = None          # transcript folder to scan
    index_path: str = "knowledge-index.md"     # the markdown deliverable
    state_path: str = "knowledge-index.state.json"  # lightweight merge cache
    workdir: str = ".knowledge-index.work"     # where transcript briefs are written

    supported_extensions: tuple[str, ...] = DEFAULT_SUPPORTED_EXTENSIONS
    recursive: bool = True

    # Near-duplicate rules (Jaccard over statement keywords) are merged, not
    # re-added, so the same rule said in three meetings becomes one entry with
    # three sources.
    dedup_threshold: float = 0.6

    # Document framing.
    title: str = "Knowledge Index"
    intro: str = ""

    # Optional seed taxonomy: ordered list of {"name": ..., "prefix": ...}. If
    # omitted, categories and id prefixes are inferred from the items as they
    # arrive. Seeding keeps ids stable and the output aligned to a known structure.
    categories: list[dict] = field(default_factory=list)

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Optional[str] = None, **overrides: Any) -> "Config":
        data: dict[str, Any] = {}
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            data = _load_yaml(text) if path.endswith((".yaml", ".yml")) else json.loads(text)
        cfg = cls()
        known = set(cfg.__dataclass_fields__)
        clean = {k: v for k, v in data.items() if k in known}
        if isinstance(clean.get("supported_extensions"), list):
            clean["supported_extensions"] = tuple(clean["supported_extensions"])
        cfg = replace(cfg, **clean)
        if overrides:
            cfg = replace(cfg, **{k: v for k, v in overrides.items() if k in known})
        return cfg


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("YAML config requested but PyYAML is not installed; use JSON.") from exc
    return yaml.safe_load(text) or {}
