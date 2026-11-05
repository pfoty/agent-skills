---
name: transcript-knowledge-base
description: >-
  Build a curated, categorized KNOWLEDGE INDEX from a folder of conversation
  transcripts (Copilot/Teams exports; .docx/.txt/.json/.vtt/.srt/.csv).
  Output is a single markdown document — like a business-rules or requirements index
  — where each entry is a clean canonical statement with a stable ID and a citation
  to the meeting, speaker, and timestamp it came from. Use whenever
  the user wants to turn meeting transcripts into a sourced rules/requirements/
  decisions index, distill discovery calls into a durable spec-style document, answer
  "what did we decide about X and where did that come from", or periodically fold
  newly added transcripts into an existing index without redoing prior work.
  Triggers: "build a knowledge index / rules doc from these transcripts", "extract
  the business rules/requirements/decisions from these meetings with sources",
  "update the index with new transcripts", "where did this rule come from". Prefer it
  even if the user just says "summarize what we agreed across these calls, with sources."
---

# Transcript Knowledge Index

Turn a folder of transcripts into a **curated markdown index of durable knowledge**
— rules, decisions, requirements, constraints, scope — each with a stable ID and
provenance (meeting, date, speaker, timestamp, verbatim quote). Output is one
markdown file plus a small JSON state cache for incremental re-runs. **No database.**

The Python tool does the mechanical work (scan, change-detect, parse `.docx`/etc.,
dedup, render). **You do the synthesis** — reading transcripts and writing clean,
spec-quality statements — which is what gives the output its quality.

## The workflow (run these in order)

### 0. Preflight — confirm Python is available (do this once, first)

The mechanical steps below run a bundled Python tool. Before the first `python -m tkb.cli`
call, verify a suitable interpreter is on PATH:

```bash
python --version    # need 3.10+ ; also try python3 / py -3 if python is missing
```

- **If it prints 3.10 or newer:** proceed to step 1. Use whichever command worked
  (`python`, `python3`, or `py -3`) for every command in this skill.
- **If it prints an older version:** use a 3.10+ interpreter if one is installed
  (`python3.11`, `py -3.11`, …); otherwise install a newer Python as below.
- **If no interpreter is found → stop and tell the user; do not fake the output.**
  The tool needs **Python 3.10+**, standard library only — **no pip install is required**
  (`requirements.txt` lists only optional extras). Offer these install paths and wait
  for the user to install, then re-run this preflight:
  - **Windows:** `winget install Python.Python.3.12` (or install from https://python.org and check "Add python.exe to PATH"). Open a new terminal afterward.
  - **macOS:** `brew install python@3.12` (or install from https://python.org).
  - **Linux:** `sudo apt install python3` / `sudo dnf install python3` (or your distro's package manager).

Never hand-write the index without the tool — the deterministic scan, change-detection,
dedup, and provenance checks are what make the output trustworthy.

### 1. Prepare — find what's new and get readable briefs

```bash
python -m tkb.cli prepare --folder "<transcripts folder>" --state knowledge-index.state.json
```

This scans the folder, compares content hashes against what's already indexed, and
writes a citation-tagged **brief** for each new/changed transcript into the work
dir (`.knowledge-index.work/`). It prints the list to process and a manifest path.
Unchanged transcripts are skipped — that is the incremental behavior, so this same
command is both initial and incremental indexing.

### 2. Extract — read each brief, produce knowledge items

For each brief in the work dir, read it and extract durable knowledge items using
the contract in [`prompts/index_extraction_prompt.md`](prompts/index_extraction_prompt.md).
Hold to these rules — they are what make the index trustworthy:

- A statement is **declarative and spec-style**, e.g. "Users authenticate via SSO
  through the corporate identity provider." — not a quote or a paraphrase of chatter.
- **Precision over volume.** A meeting yields a handful of real rules, not dozens.
  Skip greetings, status, tangents, opinions-in-passing.
- **Every item carries ≥1 source** with a real `turn_id` and a short `quote` copied
  from the brief. Never invent a citation. If you can't cite it, drop it.
- Set `status` (`confirmed`/`tentative`/`draft`/`pending`/`deferred`/`superseded`)
  and a short `note` rather than burying caveats in the statement.

When transcripts are many or long, process them in batches and merge after each
batch (the dedup step links repeats across meetings). Write the items for a
batch to `items.json`:

```json
{
  "processed_files": [ {"path": "<abs path>", "name": "<file>", "hash": "<from manifest>", "meeting": "...", "date": "..."} ],
  "items": [ { "category": "...", "statement": "...", "status": "confirmed", "sources": [ {"meeting":"...","date":"...","speaker":"...","timestamp":"...","quote":"...","turn_id":"t0042"} ] } ]
}
```

Copy each file's `hash` from the manifest's `files[]` so `merge` can mark it
ingested (that is what makes the next run skip it).

### 3. Merge — fold items into the index (dedup + provenance)

```bash
python -m tkb.cli merge --items items.json --state knowledge-index.state.json
```

Near-duplicate statements (same rule said in several meetings) are merged into one
item with multiple sources — evidence is never discarded. Items missing provenance
are dropped (and reported). IDs are assigned per category (e.g. `BID-1`, `BID-2`).

### 4. Render — write the deliverable

```bash
python -m tkb.cli render --out knowledge-index.md --state knowledge-index.state.json
```

Produces the markdown: per-category tables of `| ID | Rule | Sources |` with status
folded inline, plus an **Evidence** appendix giving the verbatim quote, speaker,
and timestamp behind every ID.

## Categories and IDs

Group items into stable categories with short ID prefixes (Authentication → `AUTH`,
Bidding → `BID`, …). Two ways to set the taxonomy:

- **Let it emerge:** just put a sensible `category` on each item; the tool derives a
  prefix and orders categories by first appearance.
- **Seed it (recommended for a known domain):** pass a `--config config.json` whose
  `categories` is an ordered list of `{"name": ..., "prefix": ...}`. This keeps IDs
  and section order stable across runs and lets you mirror an existing rules doc.
  Also set `title` and `intro` there.

Reuse an existing item's category names exactly so new rules land in the right
section and IDs stay consistent.

## Incremental re-runs

Re-running `prepare` on the same folder surfaces only new/changed transcripts (by
content hash). Extract → merge → render again; existing rules gain new sources,
genuinely new rules get new IDs, and superseded ones can be marked. Safe to run on
a schedule — see README.md §Scheduling.

## Guardrails

- Never write a statement you cannot cite to a turn in a brief.
- Don't paraphrase dialogue into the index verbatim — synthesize the *rule*, keep
  the quote in the source.
- Don't delete superseded items; mark `status: superseded` and link via `supersedes`.
- Keep statements atomic — one rule per item. Split compound statements.

## Reference

`README.md` — architecture, data model, config, scheduling, troubleshooting.
`examples/demo.py` — a runnable end-to-end example with sample transcripts.
`tests/` — expected behavior of the deterministic tooling.
