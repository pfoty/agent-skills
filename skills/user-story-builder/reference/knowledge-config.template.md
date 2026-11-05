# user-story-builder — Project Knowledge Config

```
config_version: 1
```

Saved per project at `Knowledge/user-story-builder.config.md` (default) or `.claude/user-story-builder.config.md` (fallback). The skill provisions this file on first run via discovery-assisted intake — you normally don't create it by hand, but you can edit it anytime. Everything the `user-story-builder` skill needs to adapt to *this* project lives here. Leave a field blank or `None` when it does not apply — a blank field changes the skill's behavior (it drops to a lower mode or omits a section), it does not make the skill guess. To regenerate from scratch, tell the skill to "reconfigure."

---

## 1. Source mode
Pick one. If you leave this blank, the skill infers it from what's available.

- `mode:` **A** (curated corpus) | **B** (sparse source) | **C** (conversational only)

- **A — Curated corpus:** a defined set of authoritative, ID-bearing docs is the source of truth. Strict citation enforced.
- **B — Sparse source:** a SOW / ticket / requirements doc exists but no ID scheme. Cite by name/section; never invent IDs.
- **C — Conversational only:** the only source is the request. Everything beyond it is an Assumption or Open Question.

## 2. Authoritative sources (source of record)
Only these may be cited as the source of record. List folders and/or files. Leave blank in Mode B/C.

```
authoritative_root:            # e.g. Knowledge/Docs/   (blank if none)
authoritative_sources:
  # - Knowledge/Docs/business-rules.md
  # - Knowledge/Docs/adr/            (all accepted ADRs)
  # - <add your project's files>
```

## 3. Supplemental sources (inform only — never cited as record)
These shape scope but are not citable as the source of record, except under the discrepancy rule (§5).

```
supplemental_sources:
  # - Knowledge/Transcript Knowledge.md
  # - <requirements .docx, meeting notes, wiki, etc.>
```

## 4. ID & ADR conventions
How rules and decisions are referenced. Leave blank if the project has no ID scheme (forces Mode B behavior for citation).

```
rule_id_scheme:      # e.g. PLAT-1-4, AUC-17, or R-001 from a PRD  — describe the pattern, or None
adr_convention:      # e.g. ADR-0028, folder Knowledge/Docs/adr/  — or None
id_rule: "Any ID cited in a story must resolve to a real file in an authoritative source. Do not invent IDs."
```

## 5. Two-tier discrepancy handling
Enable only if you maintain a hard authoritative/supplemental split.

```
two_tier_enabled:  true | false
# When true and a supplemental source contradicts an authoritative one on a MATERIAL point:
#   state both positions, name the supplemental source explicitly, add an Open Question.
#   Do not silently override the authoritative source.
```

## 6. Scope-guard artifacts
Declare which exist. The skill only references artifacts you mark present.

```
sow_present:        true | false     # "Deliverables-Based SOW" or equivalent scope guard
estimate_present:   true | false     # line-item estimate that Assumptions can be carried from
```

## 7. Persona / role vocabulary
The specific, contextual roles this project's stories should use in "As a …". Replaces generic "user".

```
roles:
  # - Regional Sales Manager        (internal)
  # - Registered customer           (external end user)
  # - <project personas>
pm_has_repo_access:  true | false    # false => express requirements in business/behavioral terms only
```

## 8. Codebase architecture vocabulary
Only fill this in if the project has house conventions engineering wants reflected in Technical Notes. Otherwise leave blank and the skill describes behavior generically.

```
entity_base_options:   # e.g. Entity / Auditable / SoftDeletable / Concurrent  — or blank
permission_model:      # e.g. a Permission enum; name the doc that defines names  — or blank
tenancy_term:          # e.g. Division-scoped | Tenant | Org | None
```

## 9. Tags & review policy
```
required_tags:
  # - Review Required     # tag(s) every created story must carry; signals human review
```

## 10. Design assets
```
design_asset_source:   # e.g. Figma project link, wireframe location, or None
```

## 11. Publishing target
Set only if stories should be pushed to a tracker. The skill loads the matching adapter under `reference/adapters/`. **Field mappings are resolved by the adapter, not filled in by hand** — the adapter scans the tracker for available fields/work-item types, prompts you for anything that doesn't match the expected names, and writes the resolved map back here (setting `fields_resolved: true`). Leave the mapping blank on a fresh project and let first-publish resolution populate it.

```
publishing:
  target:                # azure-devops | jira | github | linear | none
  organization:          # e.g. https://dev.azure.com/<org>
  project:               # tracker project name

  # --- resolved by the adapter on first publish; do not hand-edit unless re-mapping ---
  work_item_type:        # e.g. User Story | Product Backlog Item  (detected)
  fields_resolved:       false          # adapter sets true once the map is confirmed
  fields_resolved_for:                  # <org>/<project> the map was resolved against; re-scan if this changes
  field_mappings:
    title:               # System.Title
    description:         # System.Description   (single rich-text field, HTML not markdown)
    acceptance_criteria: # Microsoft.VSTS.Common.AcceptanceCriteria | fold-into-description
    tags:                # System.Tags | unavailable
    blocked_reason:      # Custom.BlockedReason | unavailable
  parent_link:           # link each story under the provided Feature
```

To force the adapter to re-detect fields (e.g. after a process-template change), set `fields_resolved: false` or tell the skill to "reconfigure publishing."

---

### How the skill uses this file
- Missing `authoritative_sources` + missing `rule_id_scheme` ⇒ Mode B (cite by name, no IDs).
- Missing every source ⇒ Mode C (transcribe the request; the rest is Assumptions/Open Questions).
- `sow_present: false` ⇒ the skill never invokes "the SOW" as a scope guard.
- `estimate_present: false` ⇒ Assumptions are not framed as "carried from the estimate."
- Empty codebase vocabulary ⇒ Technical Notes describe behavior generically, no house base-class names.
- `publishing.target: none` ⇒ output stays as portable markdown; nothing is pushed.
