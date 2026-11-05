# Anchored Knowledge Templates

Copy-paste templates for the two-layer knowledge system. Keep entries short, sourced, and easy to supersede. Reference Layer files are kebab-case under `docs_dir` (the Docs folder: `<project>/Knowledge/Docs/`, or `<repo>/docs/` in a repo). Governance files are under `knowledge_root`. Adapt names/prefixes to the project and record any deviations in `anchored-knowledge.config.md`.

---

# Reference Layer (source of record, in `docs_dir`)

## Glossary (`glossary.md`)

```markdown
# Glossary

## <Category, e.g. Core Concepts>

| Term | Definition |
|------|-----------|
| **Term** (Alias) | Precise definition for someone new to the domain. Link the governing rule (see business rule PREFIX-N). |
| **Renamed Term** (Business Label) | Definition. Historical note: this concept was earlier called "Old Name"; the rename is recorded in ADR-NNNN. |

## <Next Category, e.g. Systems & Integration>

| Term | Definition |
|------|-----------|
| **Term** | Definition. |
```

## Business Rules (`business-rules.md`)

```markdown
# Business Rules

This document defines the business rules for <project> based on <discovery sessions, requirements documents, and other baseline sources>.

---

## 1. <Topic>

| ID | Rule |
|----|------|
| PREFIX-1 | One self-contained, testable rule. A rule with no marker is confirmed. Write field and entity names in backticks (`EntityName.FieldName`) and key decisions in **bold**. |
| PREFIX-2 | (Draft: pending <stakeholder> confirmation as of YYYY-MM-DD.) Proposed rule text. |
| PREFIX-3 | Rule text with a decided clause (confirmed YYYY-MM-DD). Related limits are governed separately (see PREFIX-1, PREFIX-2). |
| PREFIX-4 | Rule text that depends on a decision ([ADR-NNNN](adr/NNNN-kebab-title.md)). Detailed mechanics are in [<topic>.md](<topic>.md). |
| PREFIX-5 | Rule text. The <detail> is **pending final <stakeholder> confirmation**. |
| PREFIX-6 | Rule text. *(Supersedes the earlier <understanding>; confirmed YYYY-MM-DD.)* |
| PREFIX-7 | <Feature> was discussed but is **not in Phase N scope**. Deferred to a future phase. |

## 2. <Next Topic>

| ID | Rule |
|----|------|
| NEXT-1 | Rule text. |
```

Rules:
- Two columns only. Status and provenance go inside the rule text as the inline markers above. Every marker has a date.
- Each `## N. Topic` section owns one uppercase prefix. The prefix is not in the heading. No two sections share a prefix.
- IDs are immutable, never reused, never deleted. Deprecate in place (PREFIX-7). Refine in place. Split when a rule grows two ideas, and cross-reference both rules.
- A new rule takes the next free number in its section. Use `PREFIX-0` only for a basic rule that must come before rule 1. Never renumber.
- Provenance: each Source Register row names the rule IDs that the source updated. Add an inline `SRC-…` only when two or more sources have the same date.
- When a rule needs long mechanics (state machines, formulas, message contracts), put them in a reference doc and link to it.

## Scope & Assumptions (`assumptions.md`)

```markdown
# Assumptions

## <Feature Area>

1. <Capability>
   1. Included
      1. Behavior in scope. (deciding source: date + stakeholder, SOW section, or SRC-...)
   1. Not Included
      1. Behavior out of scope or deferred. (source)

1. <Next Capability>
   1. Included
      1. Behavior in scope.
```

Put unknowns in the open-questions register (`Q-NNNN`) and link the question from the related rule. Do not keep open questions in this file.

## Decision Record (`adr/NNNN-kebab-title.md`)

```markdown
---
type: ADR
title: "ADR - Decision Title"
status: proposed | accepted | superseded | deprecated | rejected
created: YYYY-MM-DD
deciders: []
tags: [domain/architecture, activity/decision, area/<area>]
relatedTo:
  - "NNNN-related-adr-file-stem"
supersedes: []
dependsOn: []
confidence: low | medium | high
summary: "One sentence. This text is also the ADR index summary."
---

# ADR - Decision Title

## Status

**Accepted** | YYYY-MM-DD · **Addendum** YYYY-MM-DD

> **Addendum (YYYY-MM-DD): short title.** Dated note for a non-reversing refinement. Name the source (and CH-NNNN when one exists).

## Context

Why this decision is needed. Name the problem and the constraints.

## Decision

What was decided. Use subsections for scope rules (for example, when the decision does not apply).

## Rationale

Why this option is better than the alternatives.

## Consequences

### Easier

- Benefits.

### Harder

- Costs, risks, limitations, follow-up work.

## Alternatives Considered

### Alternative 1: <name>

Description and the reason it was rejected.

## Assumptions

- Conditions that must stay true for this decision to hold.

## Future Review

The event or date that triggers a review of this decision.

## Related

- Rules (PREFIX-N), other ADRs, reference docs, work items.
```

## ADR Index (`adr/INDEX.md`)

```markdown
# Architecture Decision Records

This index provides a quick reference for all ADRs. Read the full ADR only when its summary is relevant to the change at hand.

| ADR | Status | Summary |
|-----|--------|---------|
| [0001](0001-kebab-title.md) | accepted | One-sentence summary (copy of the ADR frontmatter `summary`). |
```

## Convention Doc (`<topic>-conventions.md`)

```markdown
# <Topic> Conventions

## Purpose

The purpose of this document is to define the conventions for <topic> in <project>, so that <outcome, e.g. the APIs are consistent and predictable>.

## General Principles

- **Principle**
  - Detail.

## <Convention Area>

Rules, naming patterns, and examples. Link the ADR that set the convention (ADR-NNNN).
```

## Domain Reference Doc (`<topic>.md`)

```markdown
# <Topic>

## Purpose

What this document describes and which rules depend on it (see PREFIX-N).

## <Section>

Data model, mapping table, integration contract, workflow, or environment detail.
```

## Meeting / transcript sources (delegated — no template here)

This skill does **not** hand-write meeting notes. Run the **`transcript-knowledge-base`**
skill on the transcripts folder; it produces a sourced, incremental transcript index
(default `transcript-knowledge.md`) with per-turn citations. Register that index in the
Source Register (below) as a supplemental source, then reconcile its items into the
Reference Layer via the ingestion pipeline in `SKILL.md`.

---

# Governance Layer (sourcing & change control)

## Source Register Entry

```markdown
| Source ID | Source Name | Type | Date | Owner/Provider | Location | Authority Level | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SRC-0001 | Example SOW | SOW | YYYY-MM-DD | Client/team | Link or path | 1 - Contractual baseline | What it was used to update, with the rule IDs (for example "Used to update `business-rules.md` PREFIX-3, PREFIX-6"); caveats. |
```

The Notes column is how a rule's inline date traces back to its source. Always name the rule IDs, ADRs, and glossary terms that a source updated.

## Intake Entry

```markdown
## Intake - YYYY-MM-DD - Short Title

**Captured by:** Name or agent
**Source:** Meeting, transcript, email, file, chat, stakeholder
**Triage status:** Untriaged | Converted | Archived

Raw notes:
-

Triage destination:
- Reference Layer (rule/glossary/assumption/ADR):
- Open question:
- Scope watch:
- Knowledge change:
- Source register:
```

## Open Question

```markdown
## Q-0001 - Question Title

**Status:** Open | Partial | Answered | Blocked | No Longer Needed
**Owner:** Name or role
**Needed by:** YYYY-MM-DD or milestone
**Source/anchor:** Source IDs, rule IDs, links
**Related:** Rules, decisions, scope-watch items

**Question**
The unresolved question.

**Current best answer**
What is known so far.

**Next action**
Who will ask or decide, and where the answer is recorded.

**Final answer**
Answer, date, source. Promote durable knowledge into a rule/ADR and link it here.
```

## Scope Watch Item

```markdown
## SW-0001 - Watch Item Title

**Status:** Watch | Clarify | In Scope | Deferred | Change Request | Closed
**Owner:** Name or role
**Baseline anchor:** Contract/SOW/approved-requirement source
**New/requested behavior anchor:** Meeting/client/source reference
**Related:** Rules, open questions, change requests

**Why this may be added scope**
Short explanation.

**Recommendation**
In scope, clarify, defer, or route to change control.

**Disposition**
Final outcome, date, source.
```

## Knowledge Change Entry

```markdown
## CH-0001 - Short Change Title

**Date identified:** YYYY-MM-DD
**Change type:** Contradiction | Scope Refinement | Terminology Shift | Decision Update | Requirement Update | Source Correction
**Status:** Proposed | Accepted | Needs Review | Closed
**Owner:** Name or role
**Older anchors:** Source/rule/decision IDs
**Newer anchors:** Source/Q&A/transcript/decision/change-request links
**Affected entries:** rule IDs, ADRs, Q, SW

**Previous understanding**
What the team believed and where it came from.

**New understanding**
What changed and which newer source supports it.

**Interpretation**
Contradiction vs. refinement vs. terminology shift vs. decision/requirement update vs. source correction.

**Action taken**
- Updated affected entries with dated History/amendment notes.
- Preserved superseded assumptions with anchors.
- Created/updated open questions, scope-watch items, decisions as needed.
```

## Knowledge Index

```markdown
# Knowledge Index

## How to Use This Knowledge System
- Reference Layer (source of record, in the Docs folder): glossary, business-rules, assumptions, ADRs, convention docs, domain reference docs.
- Supplemental: transcript index (from transcript-knowledge-base), intake, raw sources.
- Governance Layer: source register, open questions, scope watch, change log, intake.

## Project Baseline
- Contract/SOW:
- Approved requirements:
- Delivery baseline:

## Current Priorities
- High-impact decisions:
- Open questions needing answers:
- Scope-watch items:
- Ingestion backlog:

## Recently Changed Knowledge
- YYYY-MM-DD: CH-NNNN …

## Review Cadence
- Discovery / Estimation / Implementation / Handoff.
```

## Anchored Entry (optional `K-NNNN`, for citable facts that aren't rules)

```markdown
## K-0001 - Short Knowledge Title

**Status:** Draft | Confirmed | Needs Review | Superseded | Rejected | Scope Watch
**Type:** Fact | Requirement Detail | Assumption | Constraint
**Confidence:** Low | Medium | High
**Owner:** Name or role
**Captured:** YYYY-MM-DD
**Last reviewed:** YYYY-MM-DD
**Applies to:** Area, feature, workflow, integration, or domain
**Anchors:** Source IDs, links, meeting dates, stakeholder answers
**Related:** Rules, ADRs, open questions, scope-watch items

**Statement**
One clear durable statement.

**Implications**
- Delivery, design, testing, scope, risk, or support implications.

**History**
- YYYY-MM-DD: CH-NNNN changed/refined this entry because newer source X clarified Y. Prior assumption anchored at SRC-NNNN.
```
