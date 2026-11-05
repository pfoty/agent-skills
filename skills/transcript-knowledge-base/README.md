# transcript-knowledge-base — Knowledge Index

Turn a folder of conversation transcripts into a **curated, categorized markdown
index of durable knowledge** — rules, decisions, requirements, scope — where each
entry has a stable ID, a clean canonical statement, and a **citation back to the
meeting, speaker, timestamp, and exact quote** it came from.

The output looks like a hand-written business-rules document, but every rule is
sourced. Output is **one markdown file** (`knowledge-index.md`) plus a small JSON
state cache for incremental re-runs. **No database.**

Runs on the Python standard library (3.10+). The mechanical work is deterministic
Python; the *synthesis* (raw dialogue → clean canonical rules) is done by the agent
running the skill — see `SKILL.md`.

---

## What the output looks like

```markdown
## Authentication & Access
| ID | Rule | Sources |
|----|------|---------|
| AUTH-1 | Users authenticate via SSO through the corporate identity provider; local accounts are not supported. | Requirements Workshop (2026-02-02; Dana Lee); Security Review (2026-02-18; Priya N.) |
```

Status (`deferred`, `draft`, `superseded`, …) is folded inline on the rule, the
way a curated doc flags drafts and out-of-scope items. The Sources cell names the
meeting, date, and speaker(s). The **full verbatim quotes and timestamps are kept
in the state file** — not rendered into the document — so the file stays compact
as the corpus grows. (Need the exact words behind a rule? They're in
`knowledge-index.state.json`, keyed to the same item.)

---

## Architecture

```
transcripts/ (.docx .txt .json .vtt .srt .csv)
   │  parsers/ + normalizer        format -> turns (speaker, timestamp, text)
   ▼
prepare.py    scan + content-hash change detection + citation-tagged briefs
   │
   ▼  [ the agent reads briefs and extracts knowledge items — see SKILL.md ]
   ▼
index.py      merge (dedup + provenance) -> KnowledgeIndex
   │            • near-duplicate rules across meetings merge into one item w/ many sources
   │            • explicit supersedes marks the older item, evidence kept
   ▼
render        knowledge-index.md  (+ knowledge-index.state.json for incremental)
```

Layers: **source/change-detection** (`prepare.py`, hashes), **canonical
conversation** (`parsers/`, `normalizer.py`), **knowledge** (`index.py`:
`KnowledgeItem`, `Source`, merge/dedup, render), **state** (the JSON sidecar +
`ingested_files`).

`.docx` is the primary format (Microsoft Copilot / Teams meeting exports); the
parser ([`tkb/parsers/docx_parser.py`](tkb/parsers/docx_parser.py)) handles all
three Copilot/Teams layouts with no `python-docx` dependency.

---

## Data model

- **Source** — provenance for one item: meeting, date, speaker, timestamp, quote,
  file, turn_id. *No item is stored without at least one.*
- **KnowledgeItem** — id, category, statement, status
  (`confirmed|tentative|draft|pending|deferred|superseded`), note, related[],
  supersedes[], sources[].
- **KnowledgeIndex** — items keyed by id, ordered categories with id prefixes,
  `ingested_files` (path → hash), persisted to the JSON state and rendered to md.

---

## The workflow

```bash
# 1. scan the folder; write briefs for new/changed transcripts (incremental engine)
python -m tkb.cli prepare --folder ./Transcripts --state knowledge-index.state.json

# 2. (the agent reads the briefs in .knowledge-index.work/ and writes items.json)

# 3. fold items into the index — dedup near-duplicates, keep all provenance
python -m tkb.cli merge --items items.json --state knowledge-index.state.json

# 4. write the deliverable
python -m tkb.cli render --out knowledge-index.md --state knowledge-index.state.json

python -m tkb.cli status --state knowledge-index.state.json
```

`prepare` is both initial and incremental: unchanged files (by content hash) are
skipped, so re-running only surfaces what's new.

### items.json shape (the agent's output)

```json
{
  "processed_files": [{"path": "...", "name": "...", "hash": "<from manifest>", "meeting": "...", "date": "..."}],
  "items": [{
    "category": "Checkout",
    "statement": "Saving an order saves a draft and is distinct from submitting it.",
    "status": "confirmed",
    "sources": [{"meeting": "Scope Discussion", "date": "2026-01-21", "speaker": "Sam Ortiz",
                 "timestamp": "17:03", "quote": "saving a draft, not submitting", "turn_id": "t0080"}]
  }]
}
```

---

## Configuration

Pass `--config config.json` (or YAML with PyYAML). Keys: `title`, `intro`,
`index_path`, `state_path`, `workdir`, `supported_extensions`, `recursive`,
`dedup_threshold`, and `categories` (an ordered `[{name, prefix}]` seed taxonomy
that keeps IDs and section order stable — recommended for a known domain). See
`config.example.yaml` for the full set of options.

---

## Incremental re-runs & scheduling

Because state is keyed on content hash and IDs are stable, re-running is safe:
existing rules gain new sources, genuinely new rules get new IDs, superseded ones
are marked (evidence retained). To run on a schedule, wrap the four-step workflow
in a script and trigger it with cron / Task Scheduler. The deterministic steps
(`prepare`/`merge`/`render`) are idempotent; only the agent extraction step needs
the model.

**Windows Task Scheduler (daily):**
```powershell
$a = New-ScheduledTaskAction -Execute "python" -Argument "-m tkb.cli prepare --folder C:\Transcripts --state C:\kb\index.state.json"
Register-ScheduledTask -TaskName "KB Prepare" -Action $a -Trigger (New-ScheduledTaskTrigger -Daily -At 7am)
```

---

## How provenance is preserved

- Every `KnowledgeItem` is built with ≥1 `Source`; `validate()` rejects any with
  empty sources, and `merge` **drops** unsourced items (and reports the count).
- Merging duplicates **appends** sources — evidence is never discarded. The
  rendered doc shows meeting/date/speaker; the verbatim quote + timestamp + turn-id
  stay in the state file (queryable, kept out of the doc for size).
- Supersession marks the older item `superseded` and keeps its sources.

---

## Known limitations (read before running at scale)

The deterministic tooling (parse, change-detect, merge, render) scales cleanly —
thousands of items, large `.docx` corpora, sub-second merges. The *quality* limit
is in extraction, and it is domain-independent:

- **Over-extraction.** Status/standup meetings tempt the extractor into recording
  project status ("X is assigned to Y", "behind a feature flag") as if it were a
  durable rule. Hold the precision bar (SKILL.md) — a meeting yields a handful of
  real items, not dozens.
- **Under-consolidation across meetings.** Dedup is lexical (Jaccard over keywords);
  the same rule phrased differently in two meetings may not auto-merge, so one topic
  can sprawl across several items. Lower `dedup_threshold` to merge more
  aggressively, or add a curation pass.
- **When a corpus is large (dozens of transcripts), treat the generated index as a
  fully-sourced _superset_ to curate**, not a finished document. A human (or a
  dedicated consolidation step) should prune status items and merge near-duplicates.
- **Speaker attribution depends on the source.** Some exports (e.g. newer Copilot
  `-en-US` files) carry no speaker labels; citations then show meeting + date only.

## Tests

```bash
python -m unittest discover -s tests -t tests      # stdlib, no deps
```

Covers parsers (incl. `.docx` and malformed input), id assignment, dedup/merge,
supersession, provenance enforcement, markdown rendering/escaping, change
detection, and the full prepare→merge→render→incremental CLI lifecycle.

## Demo

```bash
python examples/demo.py
```

Runs prepare → merge → render → incremental on sample transcripts and prints the
resulting index, proving a restated rule folds into one item with two sources.

## Troubleshooting

| Symptom | Fix |
|---|---|
| A file shows `error` in the manifest | Malformed/unsupported; other files still process. |
| Re-run reprocesses everything | File content changed (hash differs). |
| Two similar rules didn't merge | Lower `dedup_threshold`, or align the statements. |
| Wrong/unstable IDs | Seed `categories` with explicit prefixes in the config. |
| `.docx` won't parse | Confirm it's a real Word file (a zip with `word/document.xml`). |
