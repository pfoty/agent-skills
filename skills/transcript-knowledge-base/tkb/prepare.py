"""Prepare transcripts for extraction.

Responsibilities (all deterministic, no LLM):

1. Scan the folder, hash each supported transcript, and compare against the
   index's record of already-ingested files -> new / changed / unchanged. This is
   the incremental engine: unchanged files are skipped, so re-runs only surface
   what's new.
2. Render each to-process transcript into a compact, *citation-tagged* brief:
   every turn is prefixed with a turn id, timestamp, and speaker so the agent can
   cite exact provenance. Briefs are written to a work directory.
3. Emit a manifest the agent (and the later ``merge`` step) can use to attribute
   sources and mark files as ingested.

The agent reads the briefs, extracts canonical knowledge items with citations,
and feeds them back through ``KnowledgeIndex.merge_item``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .config import Config
from .index import KnowledgeIndex
from .parsers import ParseError, parse_file
from .utils import sha256_file


@dataclass
class Discovered:
    path: str
    name: str
    ext: str
    content_hash: str


def discover(folder: str, config: Config) -> list[Discovered]:
    exts = {e.lower() for e in config.supported_extensions}
    out: list[Discovered] = []
    walker = os.walk(folder) if config.recursive else [(folder, [], os.listdir(folder))]
    for root, _dirs, files in walker:
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            if ext not in exts:
                continue
            path = os.path.abspath(os.path.join(root, name))
            try:
                out.append(Discovered(path, name, ext, sha256_file(path)))
            except OSError:
                continue
    return out


def classify(index: KnowledgeIndex, discovered: list[Discovered]) -> dict[str, list[Discovered]]:
    new, changed, unchanged = [], [], []
    for d in discovered:
        prior = index.ingested_files.get(d.path)
        if prior is None:
            new.append(d)
        elif prior.get("hash") != d.content_hash:
            changed.append(d)
        else:
            unchanged.append(d)
    return {"new": new, "changed": changed, "unchanged": unchanged}


def build_brief(path: str) -> dict:
    """Parse a transcript and render a citation-tagged brief."""
    raw = parse_file(path)
    name = os.path.basename(path)
    meeting = raw.title or os.path.splitext(name)[0]
    lines = [
        f"# {meeting}",
        f"_file: {name} | date: {raw.conversation_date or 'unknown'} | "
        f"participants: {', '.join(raw.participants) or 'unknown'}_",
        "",
        "Each line is a turn. Cite the bracketed turn id when extracting knowledge.",
        "",
    ]
    for i, turn in enumerate(raw.turns):
        tid = f"t{i:04d}"
        ts = f" @ {turn.start_time}" if turn.start_time else ""
        spk = turn.speaker or "unknown"
        lines.append(f"[{tid}{ts} | {spk}] {turn.text}")
    return {
        "meeting": meeting,
        "date": raw.conversation_date,
        "participants": raw.participants,
        "n_turns": len(raw.turns),
        "brief": "\n".join(lines),
        "warnings": raw.warnings,
    }


def prepare(folder: str, config: Config, index: KnowledgeIndex, workdir: str) -> dict:
    """Discover + classify + write briefs for new/changed files. Returns a manifest."""
    os.makedirs(workdir, exist_ok=True)
    discovered = discover(folder, config)
    buckets = classify(index, discovered)
    to_process = buckets["new"] + buckets["changed"]

    files = []
    for d in to_process:
        try:
            info = build_brief(d.path)
        except ParseError as exc:
            files.append({"path": d.path, "name": d.name, "error": str(exc)})
            continue
        brief_name = os.path.splitext(d.name)[0] + ".brief.md"
        brief_path = os.path.join(workdir, brief_name)
        with open(brief_path, "w", encoding="utf-8") as fh:
            fh.write(info["brief"])
        files.append({
            "path": d.path, "name": d.name, "hash": d.content_hash,
            "meeting": info["meeting"], "date": info["date"],
            "n_turns": info["n_turns"], "brief_path": brief_path,
            "warnings": info["warnings"],
        })

    manifest = {
        "folder": os.path.abspath(folder),
        "workdir": os.path.abspath(workdir),
        "counts": {
            "new": len(buckets["new"]),
            "changed": len(buckets["changed"]),
            "unchanged": len(buckets["unchanged"]),
            "to_process": len(to_process),
        },
        "unchanged": [d.name for d in buckets["unchanged"]],
        "files": files,
    }
    with open(os.path.join(workdir, "_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return manifest
