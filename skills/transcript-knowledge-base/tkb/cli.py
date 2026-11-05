"""Command-line interface for the knowledge index.

The lifecycle the agent (or a human) drives:

    1. prepare  — scan the folder, detect new/changed transcripts, write briefs
    2. <extract> — the agent reads the briefs and produces items.json
    3. merge    — fold the extracted items into the index state (dedup + provenance)
    4. render   — write the knowledge-index.md deliverable

    python -m tkb.cli prepare  --folder ./Transcripts
    python -m tkb.cli merge    --items items.json
    python -m tkb.cli render   --out knowledge-index.md
    python -m tkb.cli status

All commands are thin wrappers over the library so they stay unit-testable.
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import Config
from .index import KnowledgeIndex, Source
from . import prepare as prepare_mod


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _load_index(cfg: Config) -> KnowledgeIndex:
    idx = KnowledgeIndex.load(cfg.state_path)
    idx.title = cfg.title if cfg.title != "Knowledge Index" else idx.title
    if cfg.intro:
        idx.intro = cfg.intro
    idx.dedup_threshold = cfg.dedup_threshold
    # Seed taxonomy (stable ids + ordering) before any merge.
    for c in cfg.categories:
        idx.ensure_category(c["name"], c.get("prefix"))
    return idx


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config")
    common.add_argument("--state", default="knowledge-index.state.json")
    common.add_argument("--workdir", default=".knowledge-index.work")

    p = argparse.ArgumentParser(prog="tkb", description="Transcript knowledge index", parents=[common])
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("prepare", help="Scan folder; write briefs for new/changed transcripts", parents=[common])
    sp.add_argument("--folder", required=True)

    sp = sub.add_parser("merge", help="Merge extracted items.json into the index", parents=[common])
    sp.add_argument("--items", required=True, help="JSON file with {processed_files, items}")

    sp = sub.add_parser("render", help="Write the knowledge-index.md deliverable", parents=[common])
    sp.add_argument("--out", default="knowledge-index.md")

    sub.add_parser("status", help="Show index status", parents=[common])

    return p


def _cfg(args) -> Config:
    cfg = Config.load(getattr(args, "config", None))
    cfg.state_path = args.state
    cfg.workdir = args.workdir
    return cfg


def cmd_prepare(args, cfg: Config) -> None:
    idx = _load_index(cfg)
    manifest = prepare_mod.prepare(args.folder, cfg, idx, cfg.workdir)
    _print({
        "counts": manifest["counts"],
        "workdir": manifest["workdir"],
        "manifest": f"{manifest['workdir']}/_manifest.json",
        "to_process": [f["name"] for f in manifest["files"]],
        "unchanged": manifest["unchanged"],
    })


def cmd_merge(args, cfg: Config) -> None:
    idx = _load_index(cfg)
    with open(args.items, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    created, updated, dropped = 0, 0, []
    for raw in payload.get("items", []):
        sources = [Source(**s) for s in raw.get("sources", [])]
        if not sources:
            dropped.append(raw.get("statement", "")[:60])  # provenance is mandatory
            continue
        _id, is_new = idx.merge_item(
            category=raw["category"], statement=raw["statement"], sources=sources,
            status=raw.get("status", "confirmed"), note=raw.get("note"),
            related=raw.get("related"), supersedes=raw.get("supersedes"),
            prefix=raw.get("prefix"),
        )
        created += int(is_new)
        updated += int(not is_new)

    for f in payload.get("processed_files", []):
        if f.get("path") and f.get("hash"):
            idx.mark_ingested(f["path"], f["hash"], f.get("name", ""), f.get("date"))

    idx.save(cfg.state_path)
    _print({
        "created": created, "updated": updated,
        "dropped_no_provenance": len(dropped),
        "total_items": len(idx.items), "state": cfg.state_path,
    })


def cmd_render(args, cfg: Config) -> None:
    idx = _load_index(cfg)
    md = idx.render_markdown()
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(md)
    idx.save(cfg.state_path)  # persist generated_at
    _print({
        "index": args.out, "items": len(idx.items),
        "categories": len(idx.category_order), "sources_files": len(idx.ingested_files),
    })


def cmd_status(args, cfg: Config) -> None:
    idx = _load_index(cfg)
    by_cat = {c: sum(1 for it in idx.items.values() if it.category == c) for c in idx.category_order}
    _print({
        "title": idx.title,
        "items": len(idx.items),
        "categories": by_cat,
        "ingested_files": [v["name"] for v in idx.ingested_files.values()],
        "generated_at": idx.generated_at,
    })


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = _cfg(args)
    {
        "prepare": cmd_prepare, "merge": cmd_merge,
        "render": cmd_render, "status": cmd_status,
    }[args.command](args, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
