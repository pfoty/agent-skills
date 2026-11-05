---
name: anchored-knowledge
description: Create, audit, or improve a reusable two-layer project knowledge system (a citable Reference Layer plus a sourcing/change-control Governance Layer). Use when an agent needs to turn informal memory files, meeting notes, transcripts, requirements, decisions, open questions, scope notes, or project "bits of knowledge" into sourced, durable, citable knowledge that can be reused by Claude or other agentic platforms. The Reference Layer lives in a Docs folder (Knowledge/Docs/ or a repo's docs/) with business-rules.md, glossary.md, assumptions, adr/, and convention docs; use it to write or audit business rules in that format.
---

# Anchored Knowledge

You are the **Knowledge Steward** for a project. Turn raw, unstructured inputs (transcripts, emails, SOWs, requirements, sample files, Q&A, chat, dev docs) into a single, trustworthy, traceable knowledge base the team and other agents can rely on as the source of record.

Three standing goals, in priority order:

1. **Traceability** — every durable statement is anchored to a source, or explicitly marked unconfirmed.
2. **Single source of truth** — each fact, rule, term, or decision lives in exactly one place; everything else links to it.
3. **Citability** — durable knowledge carries a stable, immutable ID so work items, stories, specs, and tests can reference it unambiguously.

Keep output **platform-neutral**: plain Markdown, stable kebab-case filenames, stable IDs, enough inline instruction that any agent or human can run the process cold. Adapt file/section names and ID prefixes to the project — if a good equivalent already exists, **improve its structure rather than renaming**, and record the real names in the config.

## Step 0 — Locate the knowledge base and load config (always first)

Every run begins here. Nothing is read or written until the base location and conventions are known, because they differ per project.

1. **Look for the config.** Check `docs/anchored-knowledge.config.md`, then `Knowledge/anchored-knowledge.config.md`, then `.claude/anchored-knowledge.config.md`. If found, load it — it declares `knowledge_root`, whether the base is git-managed, the file map, the SOW, and the ID conventions. Skip to the requested operation.
2. **If there's no config, discover the base.** Scan for an existing base: a `Knowledge/Docs/`, `docs/`, or `Knowledge/` folder, or files named like `business-rules*.md`, `open-questions*.md`, `decisions*.md`/`adr/` (with `INDEX.md` or `index.md`), `source-register*.md`, `glossary*.md`, `assumptions*.md`, `*-conventions.md`, `bits of knowledge*.md`. A folder that holds `business-rules.md`, `glossary.md`, and `adr/` together is the Docs folder (`docs_dir`).
3. **Choose two locations — a committed record and a working area.** Knowledge lives in two places; propose both defaults and let the user confirm or redirect. **Never guess silently.**
   - **`knowledge_root` — the committed source of record.** In a git repo → **`<repo>/docs/`**, so knowledge is version-controlled and shared with the team. `docs/` may also hold unrelated files; that is fine — only knowledge that has been *promoted* (confirmed) is committed here, so the folder never fills with half-finished notes. Detect the repo root with `git rev-parse --show-toplevel`. Not a git repo → `<project>/Knowledge/`.
   - **`docs_dir` — the Docs folder that holds the Reference Layer.** Business rules, glossary, assumptions, ADRs, and convention and reference docs live here. In a git repo → **`<repo>/docs/`** (the same folder as `knowledge_root`). Not a git repo → **`<project>/Knowledge/Docs/`**, with the governance files one level up in `<project>/Knowledge/`. Use the same file layout in both cases, so a project workspace's `Knowledge/Docs/` can mirror a development repo's `docs/`.
   - **`working_dir` — the working area for knowledge not yet ready for the repo.** A local staging folder for captured/drafted knowledge that should **not** be committed yet: intake, the freshly-ingested transcript index, draft entries, and proposals. Default **`<project>/Knowledge/`** (or `<repo>/knowledge-working/` if the project *is* the repo). It is **never pushed** — if it sits inside the repo, add it to `.gitignore`. Without a repo, `working_dir` can be the same folder as `knowledge_root`; keep drafts in `drafts/`.
4. **If git-managed, pair with `git-guide`.** When `knowledge_root` is inside a repo, the record is shared through Azure DevOps / GitHub and the user may be non-technical. **Do not run raw git.** Use the **`git-guide`** skill: "get the latest" before you read or edit, and "save"/"publish" after promoting approved changes into `knowledge_root`. Only `knowledge_root` is committed — `working_dir` stays local. Record `git_managed: true` and the host in the config. See *Working area, promotion & git-guide* below.
5. **Provision the config.** Create `<knowledge_root>/anchored-knowledge.config.md` from `references/knowledge-config.template.md`, filling in what you discovered. For anything unresolved — location, SOW location/name (§3), ID/ADR conventions (§4), transcript folder (§5) — **ask the user rather than assuming**, then write the answers back. This file is how the skill stays consistent across runs and reusable across projects.
6. **Adopt existing names.** If the base already uses filenames that differ from the defaults, record the real names in the config's file map and use them verbatim — never silently rename.

Reference Layer files below are relative to `docs_dir` (default `<repo>/docs/`, else `<project>/Knowledge/Docs/`). Governance files are relative to `knowledge_root` (default `<repo>/docs/`, else `<project>/Knowledge/`). Working files (intake, transcript index, drafts) live in `working_dir`. The config's file map is authoritative when it differs.

### Working area, promotion & git-guide

Knowledge matures through two directories:

- **`working_dir` (local, uncommitted)** — where knowledge is captured and drafted: intake, the transcript index, proposals, and anything still `Draft` / `Needs Review`. Nothing here is shared until it is promoted. Never pushed.
- **`knowledge_root` (committed source of record)** — the confirmed, citable knowledge the team relies on. In a repo it lives in `<repo>/docs/` and is the *only* knowledge that gets committed (it may sit alongside other, unrelated `docs/` files).

**Promotion is the one-way gate from working to record:** when an entry is approved, write it into `knowledge_root` (with its ID, anchors, and `Confirmed` status), remove/close the working draft, and — if git-managed — commit it. This keeps unfinished knowledge out of the repo while giving confirmed knowledge a stable, shared home.

When `git_managed: true`, do all git through the **`git-guide`** skill — it runs git safely in plain language, so neither you nor a non-technical user touches raw git:

- **Before reading or ingesting:** git-guide **"get the latest"** so you reconcile against the team's current record, not a stale copy.
- **After promoting approved changes into `knowledge_root`:** git-guide **"save"** (private checkpoint) then **"publish/share"** (opens a PR for review). Name the exact rule IDs you promoted in the save message.
- **Propose-then-apply still holds:** get latest → draft in `working_dir` → present proposals → on approval promote into `knowledge_root` → save/publish. Never auto-commit, and never commit `working_dir`.

## The two layers

**1. Reference Layer — the "rule standard" and source of record.** Only these may be cited downstream (stories, AC, specs). All live directly under `docs_dir` (the Docs folder):

- **Glossary** (`glossary.md`) — canonical vocabulary, grouped under `## <Category>` headings. One row per term in a `| Term | Definition |` table; write the term as `**Term** (Alias)`. Put retired aliases and links to the governing rule or ADR in the definition. Write it first; consult it first. Kills terminology drift.
- **Business Rules** (`business-rules.md`) — **the core.** Use the Docs format below. Numbered topic sections (`## N. Topic`), each owning an uppercase **ID prefix** (`AUTH`, `USER`, `ORDER`… per the config). One rule per row in a two-column `| ID | Rule |` table, `PREFIX-N`. IDs **immutable, never reused, never deleted** — deprecate in place (rewrite to say "out of scope / deferred", keep the ID). Refine in place; split when a rule grows two ideas. Each rule self-contained and testable; state mechanics (fields, formulas, thresholds) when decided; cross-link rules/ADRs inline.
- **Scope & Assumptions** (`assumptions.md`) — in/out-of-scope ledger by area (`## <Area>`), written as a nested numbered outline with **Included** / **Not Included** branches. Name the deciding source when it is known. Unknowns go to the open-questions register, not here. Makes "we never agreed to that" provable.
- **Decision Records** (`adr/` + `adr/INDEX.md`) — one file per decision (`NNNN-kebab-title.md`), sequential, never renumbered. Each ADR has YAML frontmatter (`type, title, status, created, deciders, tags, relatedTo, supersedes, dependsOn, confidence, summary`) and the sections Status, Context, Decision, Rationale, Consequences, Alternatives Considered, Assumptions, Future Review, Related. Supersede (don't overwrite) on reversal; add a dated addendum for non-reversing refinements. The index has one row per ADR; its summary is the frontmatter `summary`.
- **Convention docs** (`<topic>-conventions.md`, as needed) — how the team builds: API, build, SQL, file, and test conventions. Each starts with `## Purpose`. Business rules state *what* the system does; convention docs state *how* the team builds it.
- **Domain reference docs** (`<topic>.md`, as needed) — data model and mappings, integration contracts, authentication, environments, sitemap, detailed workflows. Keep them flat in `docs_dir`, not in a subfolder. When a rule needs long mechanics, put the mechanics here and link to the doc from the rule.
- **Supporting folders** (optional, under `docs_dir`) — for example `meetings/`, `answered-questions/`, `examples/`, `user-documentation/`. These hold supplemental material. They are not citable as source of record. Register each folder in the Source Register.
- **Transcript index** (supplemental, produced elsewhere) — meeting/call transcripts are **not** parsed by this skill. The `transcript-knowledge-base` skill turns a transcript folder into a sourced index that lands in **`working_dir`**; it is registered as a supplemental source and reconciled in, never cited directly as the source of record. See the ingestion pipeline.

### Business rules format (Docs format)

Write and keep `business-rules.md` in this format. The full template is in `references/templates.md`.

- **Header:** `# Business Rules`, one sentence that states the purpose and the baseline sources, then `---`.
- **Sections:** `## N. Topic` (numbered, Title Case). The prefix appears only in the IDs, not in the heading. Each section has one prefix; no two sections share a prefix.
- **Table:** two columns, `| ID | Rule |`. Do not add Status or Anchors columns. Status and provenance go inside the rule text.
- **Inline status markers.** A rule with no marker is confirmed. Use these markers for all other states, and always include a date:
  - Draft: start the rule with `(Draft: pending <stakeholder> confirmation as of YYYY-MM-DD.)`
  - Decided clause: put `(confirmed YYYY-MM-DD)` after the clause.
  - Open part of a rule: write `**pending final <stakeholder> confirmation**` in the sentence.
  - Superseded understanding: end the rule with `*(Supersedes <earlier understanding>; confirmed YYYY-MM-DD.)*`
  - Out of scope or deferred: rewrite the rule to say `**not in Phase N scope**. Deferred to a future phase.` Keep the ID.
  - When you read an existing file, accept an em-dash or a colon after `Draft`. Write the colon form in new text.
- **Provenance without an Anchors column.** Every Source Register row and every change-log entry names the rule IDs that it updated. The inline date points to that source. Add an inline `SRC-…` only when two or more sources have the same date.
- **Cross-links:** `(see PREFIX-8, PREFIX-9)` for rules, `[ADR-NNNN](adr/NNNN-title.md)` or `ADR-NNNN` for decisions, and the tracker ID for work items. Write field and entity names in backticks. Write key decisions in bold.
- **ID allocation:** a new rule takes the next free number in its section, even when it goes in a different row position. Use `PREFIX-0` only for a basic rule that must come before rule 1. Never renumber.

**2. Governance Layer — sourcing & change control that keeps the Reference Layer honest** (under `knowledge_root`, except intake which stays in `working_dir`):

- **Source Register** (`source-register.md`) — every source artifact: `SRC-… | Name | Type | Date | Owner | Location | Authority Level | Notes`. Cite `SRC-…` from anchored entries.
- **Intake** (`knowledge-intake.md`, in **`working_dir`**) — fast capture before triage; each entry notes source + raw bullets + triage destination. Archive once its durable content is promoted into `knowledge_root`.
- **Open Questions** (`open-questions.md`) — `Q-NNNN`, status, owner, needed-by, anchor, best answer, next action, final answer. **When answered, promote the durable answer into a rule/ADR and link back** — this is a queue, not a knowledge store.
- **Scope Watch** (`scope-watch.md`) — `SW-NNNN`: valid knowledge that may exceed baseline; baseline anchor, new behavior anchor, why, recommendation (in scope / clarify / defer / change control), disposition.
- **Knowledge Change Log** (`knowledge-change-log.md`) — `CH-NNNN` whenever a newer source refines/contradicts/supersedes older understanding (type, older vs. newer anchors, affected entries, previous vs. new understanding, interpretation, action). Add a dated `History`/amendment note to affected entries; preserve superseded assumptions with anchors.

**Authority levels (strongest→weakest; prefer higher, record conflicts, never resolve silently)** — the default ladder, overridable in the config: 1) Contractual baseline (SOW) · 2) Approved requirements · 3) Client clarification · 4) Source artifact · 5) Internal interpretation · 6) Unreviewed intake.

**Shared status vocabulary:** `Draft` · `Confirmed` · `Needs Review` · `Superseded` · `Rejected` · `Scope Watch`. In `business-rules.md`, write these states as the inline markers above (no marker = `Confirmed`). Governance entries and `K-NNNN` entries keep a `Status:` field.

## ID conventions

IDs and the ADR format come from the config (§4). If the project already uses a scheme, detect and reuse it; if you cannot reconcile it, **ask the user to confirm before minting new IDs**.

| Artifact | ID | Rule |
| --- | --- | --- |
| Business/domain rule | `PREFIX-N` (per section) | Immutable, never reused/deleted — deprecate in place. `PREFIX-0` only for a basic rule placed before rule 1 |
| Decision record | `ADR-NNNN` (file `NNNN-kebab-title.md`) | Sequential, never renumbered; supersede, don't overwrite |
| Source | `SRC-…` | Stable; carries an authority level |
| Open question | `Q-NNNN` | Closes by promotion into a rule/ADR |
| Scope-watch item | `SW-NNNN` | Routes to in-scope / defer / change control |
| Knowledge change | `CH-NNNN` | Logs every shift; adds History to affected entries |
| Anchored entry (optional) | `K-NNNN` | For citable facts that aren't rules |

## Source ingestion pipeline (run for every new source)

1. **Route by source type.**
   - **Transcripts / meeting recordings / call exports → delegate.** Do not hand-parse them here. Invoke the **`transcript-knowledge-base`** skill on the transcripts folder (config §5). It change-detects, parses, and renders a sourced, incremental transcript index with per-turn citations. **Render it into `working_dir` at the config's `transcript_index` path (default `transcript-knowledge.md`) with a matching state file — not the transcript skill's own default `knowledge-index.md` / `knowledge-index.state.json`, which would overwrite this base's `knowledge-index.md`.** Register that index in the Source Register as a supplemental source, then continue at step 2 to reconcile its items into the Reference Layer.
   - **All other sources (SOW, requirements, emails, Q&A, sample files, chat, dev docs) → capture.** Read the *full* source. Add a fast entry to `knowledge-intake.md` in **`working_dir`** (source + raw bullets + triage destination) and register the source in `source-register.md` with its authority level. **Never invent decisions.**
2. **Reconcile against the rule standard.** Read `business-rules.md` (+ glossary/assumptions) end-to-end; classify each incoming item: **Already covered** / **Conflicts** (name the rule ID) / **Refines** / **New rule** (propose ID or new section/prefix per the config). Produce a written audit with **Conflicts / Refinements / New Rules**, each giving rule ID, current text, the incoming item, recommended new text/ID. Draft `CH-NNNN` and/or `SW-NNNN` for genuine contradictions or scope shifts. Draft new/edited entries in `working_dir` — do not touch `knowledge_root` yet.
3. **Apply only with approval, then promote.** **Do not auto-edit `business-rules.md` or other `docs_dir` / `knowledge_root` docs.** Present proposals; on approval, **promote** the confirmed entries from `working_dir` into `docs_dir` (with IDs and the correct inline markers; a confirmed rule has no Draft marker and carries `(confirmed YYYY-MM-DD)` on the decided clause). Update the Source Register row for each source to name the rule IDs it updated. Report exactly which IDs changed, and — if git-managed — commit via `git-guide` (save → publish). Leave raw sources and the transcript index in `working_dir`.

## Standing operating procedures

- **A. Bootstrap.** Run Step 0 (choose `knowledge_root` + `working_dir`, provision config). Stand up both trees; if `working_dir` is inside the repo, add it to `.gitignore` and set `working_dir_gitignored: true`. **Find the SOW** — if you can't, ask the user where it is and what it's called, and record it in the config (§3). Inspect existing artifacts; preserve good structure. Seed the Source Register from the SOW/requirements (highest authority first). Draft the glossary and a `business-rules.md` skeleton from baseline docs, marking everything `Draft` until anchored. Capture every unknown as an Open Question.
- **B. Ingest a source.** Run the ingestion pipeline (transcripts → `transcript-knowledge-base`; everything else → intake), then reconcile.
- **C. Answer an open question.** Record answer + source on `Q-NNNN`, promote the durable part into a rule/ADR, link back, flag scope implications as `SW-NNNN`.
- **D. Record a decision.** Write/append the ADR, update the ADR index and affected rules. Supersede the old ADR if reversed.
- **E. Detect a knowledge shift.** Log `CH-NNNN`, add dated History/amendment notes to affected entries, preserve the old anchored assumption, classify contradiction vs. refinement vs. terminology shift.
- **F. Health-check / audit.** Verify the Quality Checklist; report gaps as a punch list.

## Default file skeleton

Two trees. All filenames kebab-case; the config's file map wins if an existing base uses other names.

**Committed record — `knowledge_root` + `docs_dir`.** Only *promoted* (confirmed) knowledge goes here. The Docs folder has the same layout in both modes.

No repo (`knowledge_root` = `<project>/Knowledge/`, `docs_dir` = `<project>/Knowledge/Docs/`):

```text
Knowledge/                          # = knowledge_root  (governance layer + config)
  anchored-knowledge.config.md      # per-project config (locations, git, SOW, ID conventions)
  knowledge-index.md
  source-register.md
  open-questions.md
  scope-watch.md
  knowledge-change-log.md
  Docs/                             # = docs_dir  (Reference Layer; mirrors a dev repo's docs/)
    business-rules.md
    glossary.md
    assumptions.md
    <topic>-conventions.md          # api / build / sql / test conventions, as needed
    <topic>.md                      # domain reference docs (auth, data mapping, environments), as needed
    adr/
      INDEX.md
      0001-<kebab-title>.md
    <supporting-folder>/            # optional, supplemental only (meetings/, examples/, ...)
```

In a git repo (`knowledge_root` = `docs_dir` = `<repo>/docs/`), the same files sit together in `docs/`, which may also hold other repo docs.

**Working area — `working_dir`** (`<project>/Knowledge/`, or `<repo>/knowledge-working/`; **gitignored / never pushed**). Holds knowledge not yet ready for the record:

```text
Knowledge/                          # = working_dir  (local, uncommitted staging)
  knowledge-intake.md               # fast capture before triage
  transcript-knowledge.md           # transcript index from transcript-knowledge-base
  drafts/                           # proposed rules/ADRs/entries pending approval
```

Approved knowledge is **promoted** from `working_dir` into `knowledge_root` and (when `git_managed`) committed via the `git-guide` skill. If `working_dir` sits inside the repo, add it to `.gitignore` so it is never pushed.

> **Source-of-record rule:** Only the Reference Layer may be cited as source of record in stories, specs, and AC. Notes, intake, transcripts/transcript index, and governance logs are supplemental — they explain *why* a rule exists; the rule is what gets built and tested. If a story needs a fact that lives only in a transcript, promote it into the Reference Layer first.

## Templates

For copy-paste templates (glossary, business rules, assumptions area, ADR + index, convention doc, open question, scope-watch, knowledge-change, source-register row, knowledge index, intake, optional anchored entry), read `references/templates.md`. For the per-project config, read `references/knowledge-config.template.md`.

## Operating principles

- **Config first.** Locate the base and load/provision the config before anything else; ask when you can't find the base, the SOW, or the ID scheme.
- **Two directories; promote to commit.** Draft in `working_dir` (local, never pushed); promote approved knowledge into `knowledge_root` (`<repo>/docs/` in a repo). Only promoted knowledge is committed, so unfinished notes never reach the repo. When git-managed, get the latest before editing and save/publish after promoting — always through the `git-guide` skill, never raw git.
- **Anchor or flag.** Every durable statement has a source, or wears `Draft`/`Needs Review`.
- **One home per fact.** Cross-link; never copy paragraphs.
- **Don't resolve conflicts silently.** Record them, prefer higher authority, open a question if needed.
- **Deprecate, don't delete.** Out-of-scope/superseded knowledge stays, clearly marked, with anchors.
- **Propose, then apply.** Never mutate the rule set without explicit approval; report exact IDs changed.
- **Cite precisely.** `SRC-…` for sources, rule/ADR IDs for cross-references; transcript-level citations live in the transcript index.
- **Match the project's voice.** Reuse existing terminology and structure; consistency beats novelty.
- State whether your output is an audit/recommendation, a new template set, or an applied migration.

## Quality checklist

- [ ] The base was located (or created) and a per-project config exists with `knowledge_root`, `docs_dir`, file map, SOW, and ID conventions recorded.
- [ ] Two directories are set: `knowledge_root` (`<repo>/docs/` in a repo, else `<project>/Knowledge/`) and a `working_dir` that is gitignored/never committed. Approved knowledge is promoted from working into the record; if git-managed, syncing goes through `git-guide`.
- [ ] Every durable statement is anchored, or marked `Draft`/`Needs Review`.
- [ ] Rules, decisions, and open questions live in separate homes — not blended.
- [ ] Possible added scope is separated from confirmed in-scope knowledge.
- [ ] Rule IDs are immutable, gap-tolerant, never reused; deprecated rules deprecated in place.
- [ ] `business-rules.md` uses the Docs format: `## N. Topic` sections, two-column `| ID | Rule |` tables, one unique prefix for each section.
- [ ] Every Draft or pending marker has a date. Every Source Register row names the rule IDs it updated.
- [ ] Every `(see PREFIX-N)` and ADR link resolves to a real rule or ADR file. Every ADR has a row in `adr/INDEX.md`.
- [ ] Knowledge shifts captured as dated `CH-NNNN`; affected entries carry History/amendment notes.
- [ ] No duplicate sources of truth; cross-links instead of copies. Transcript ingestion is delegated to `transcript-knowledge-base`, not re-implemented here.
- [ ] Source authority is explicit on every source; conflicts recorded, not hidden.
- [ ] Glossary is current; aliases/retired terms reconciled.
- [ ] Review cadence and ownership are defined.
- [ ] The Reference Layer alone is enough for a developer/spec author to act without reading raw sources.
