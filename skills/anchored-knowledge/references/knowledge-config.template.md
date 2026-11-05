# anchored-knowledge — Project Knowledge Config

```
config_version: 1
```

Saved per project at `Knowledge/anchored-knowledge.config.md` (default) or
`.claude/anchored-knowledge.config.md` (fallback). The skill provisions this file on
first run via discovery-assisted intake — you normally don't create it by hand, but you
can edit it anytime. Everything the `anchored-knowledge` skill needs to adapt to *this*
project lives here, so the skill never has to guess where the knowledge base is, what it
is called, or which ID conventions are in force. To regenerate from scratch, tell the
skill to "reconfigure."

Leave a field blank or `None` when it genuinely does not apply — a blank field changes
behavior (the skill asks, or drops a step), it does not make the skill guess silently.

---

## 1. Knowledge base location
Knowledge lives in **two directories**: a committed source of record (`knowledge_root`, with
its Docs folder `docs_dir`) and a local working area (`working_dir`) for knowledge not yet
ready for the repo.

- **`docs_dir` — the Docs folder (Reference Layer).** Business rules, glossary, assumptions,
  ADRs, and convention and reference docs. No repo: `<project>/Knowledge/Docs/`, with the
  governance files one level up in `knowledge_root`. In a git repo: `<repo>/docs/` (same folder
  as `knowledge_root`). The layout inside the Docs folder is the same in both modes.

- **`knowledge_root` — committed source of record.** In a git repo, **`<repo>/docs/`**. Without a
  repo, `<project>/Knowledge/`. This is the only tree that gets committed. `docs/` may also hold
  unrelated files — that is fine, because only *promoted* (confirmed) knowledge is committed here,
  never half-finished notes (those stay in `working_dir`).
- **`working_dir` — working area (never committed).** Local staging for intake, the transcript
  index, and drafts that are not yet promoted. Default `<project>/Knowledge/` (or
  `<repo>/knowledge-working/` if the project *is* the repo). If it sits inside the repo, it must
  be **gitignored** so it is never pushed.

The skill detects whether you are in a git repo, proposes both defaults, and asks the user to
confirm before writing anything.

```
knowledge_root:            # e.g. docs/ (repo, preferred)  |  Knowledge/ (no repo)
docs_dir:                  # e.g. docs/ (repo)  |  Knowledge/Docs/ (no repo); Reference Layer files
working_dir:               # e.g. Knowledge/  — local staging; NEVER committed (gitignore if inside the repo)
storage_mode:  repo-docs | project-knowledge
created_new:  true | false # true if the skill scaffolded it; false if an existing base was adopted

# --- git (fill when knowledge_root is inside a repo) ---
git_managed:  true | false # true => sync via the git-guide skill; never run raw git
git_host:                  # azure-devops | github | none  (from the repo remote)
git_repo_root:             # absolute path from `git rev-parse --show-toplevel`
working_dir_gitignored:  true | false   # true once working_dir is added to .gitignore (when it lives inside the repo)
```

**Promotion:** knowledge is drafted in `working_dir`, and once approved it is *promoted* into
`knowledge_root` and (when `git_managed: true`) committed via the **git-guide** skill — "get the
latest" before editing, "save" then "publish/share" after promoting. `working_dir` is never
pushed.

## 2. File map
Canonical filenames the skill reads and writes. Reference Layer files live under `docs_dir`;
governance files live under `knowledge_root`; working files live under `working_dir` (marked below). Defaults are kebab-case. **If an existing
base already uses different names, record the real names here** — the skill uses these paths
verbatim and does not rename existing files unless you ask it to.

```
# Reference Layer — committed under docs_dir (only these may be cited downstream)
glossary:            glossary.md
business_rules:      business-rules.md    # Docs format: "## N. Topic" sections, two-column "| ID | Rule |" tables, inline status markers
assumptions:         assumptions.md
adr_dir:             adr/                 # decision records folder (files NNNN-kebab-title.md)
adr_index:           adr/INDEX.md
conventions:         <topic>-conventions.md   # api / build / sql / test conventions, flat in docs_dir
reference_docs:      <topic>.md           # domain reference docs (auth, data mapping, environments), flat in docs_dir
supporting_dirs:                          # optional supplemental subfolders of docs_dir, e.g. meetings/, examples/ (not citable)

# Governance Layer — committed under knowledge_root
source_register:     source-register.md
open_questions:      open-questions.md
scope_watch:         scope-watch.md
change_log:          knowledge-change-log.md
index:               knowledge-index.md   # orientation / how-to-use doc

# Working files — under working_dir, NEVER committed
intake:              knowledge-intake.md  # (working_dir) fast capture before triage
drafts_dir:          drafts/              # (working_dir) proposed entries pending approval
# transcript_index (working_dir) is set in §5
```

## 3. SOW / scope baseline
The Statement of Work (or equivalent top-authority scope artifact) anchors the whole
authority ladder. **If the skill cannot find it, it asks the user where it is and what it
is called**, then records the answer here. On an internal project with no SOW, set
`sow_present: false` and name whatever serves as the scope baseline instead.

```
sow_present:   true | false
sow_name:                    # exact document title, e.g. "<Client> <Project> SOW v3"
sow_location:                # path or link, e.g. ../SOW/<project>-sow-v3.docx
scope_baseline_note:         # if sow_present is false, what is the top-authority scope source?
```

## 4. ID & ADR conventions
How rules and decisions are referenced. **If existing docs already use IDs, the skill
detects the pattern and records it here; if it cannot reconcile the scheme, it asks the
user to confirm it** before writing any new IDs.

```
rule_id_prefixes:            # per-topic uppercase prefixes, e.g. AUTH, USER, ORDER — or "emerge" to derive per section; one unique prefix per section
rule_status_style:  inline   # inline markers in the rule text (Docs format); no marker = Confirmed
adr_convention:  ADR-NNNN    # ID format for decision records
adr_filename:    NNNN-kebab-title.md   # file naming inside adr_dir
adr_format:      frontmatter # YAML frontmatter + Status/Context/Decision/Rationale/Consequences/Alternatives/Assumptions/Future Review/Related
id_rule: "IDs are immutable, never reused, never deleted — deprecate in place. Any ID cited downstream must resolve to a real entry."
```

## 5. Transcript ingestion (delegated)
This skill does **not** parse transcripts itself. Meeting/call transcripts are handled by
the `transcript-knowledge-base` skill, which emits a sourced, incremental index that this
skill treats as a **supplemental source** and reconciles into the Reference Layer.

```
transcripts_present:   true | false
transcripts_folder:                    # folder of raw transcripts handed to transcript-knowledge-base
transcript_index:      transcript-knowledge.md   # (working_dir) output the transcript skill renders — MUST differ from `index` above; the transcript skill defaults to knowledge-index.md and would overwrite it
```

## 6. Authority ladder
Strongest → weakest. Default suits a client-services engagement; adjust for internal
projects. The skill prefers higher authority, records conflicts, and never resolves them
silently.

```
authority_levels:
  1: Contractual baseline (SOW, signed change request)
  2: Approved requirements (accepted requirements / stories / AC)
  3: Client clarification (named stakeholder answer, approved Q&A, meeting decision)
  4: Source artifact (spreadsheet, sample file, export, current-system behavior)
  5: Internal interpretation (team analysis, inferred rule)
  6: Unreviewed intake (draft note, brainstorm, uncited memory)
```

## 7. Review cadence & ownership
```
knowledge_owner:             # person/role accountable for the base
review_cadence:              # e.g. weekly during discovery; on-change during implementation; audit at handoff
```

---

### How the skill uses this file
- No `docs_dir` set ⇒ the skill looks for a folder that holds `business-rules.md`, `glossary.md`, and `adr/`. If none exists, it proposes `<project>/Knowledge/Docs/` (no repo) or `<repo>/docs/` (repo).
- `rule_status_style: inline` ⇒ `business-rules.md` keeps two columns; status and dates go in the rule text, and Source Register notes name the rule IDs each source updated.
- No `knowledge_root` found ⇒ the skill proposes `<repo>/docs/` in a git repo (or `<project>/Knowledge/` otherwise) and records the confirmed choice. `docs/` may hold other files; only promoted knowledge is committed there.
- `working_dir` ⇒ intake, the transcript index, and drafts live here and are **never committed**; if it's inside the repo it must be gitignored.
- **Promotion** ⇒ approved entries move from `working_dir` into `knowledge_root`; only `knowledge_root` is committed.
- `git_managed: true` ⇒ the skill syncs through the **git-guide** skill (get-latest before editing; save/publish after promoting) and never runs raw git.
- Existing filenames differ from the defaults in §2 ⇒ the recorded names win; nothing is renamed silently.
- `sow_present: false` ⇒ the skill never invokes "the SOW"; it uses `scope_baseline_note` as the top authority.
- `rule_id_prefixes` unresolved ⇒ the skill asks the user to confirm the scheme before minting IDs.
- `transcripts_present: true` ⇒ transcript intake is delegated to `transcript-knowledge-base`; its `transcript_index` is registered as a supplemental source, not the source of record.
