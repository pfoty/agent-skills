You are building a **knowledge index** from a meeting transcript — a curated list
of durable, reusable knowledge items, in the style of a business-rules document.
You will be given one transcript brief whose every line is a turn tagged with a
turn id, timestamp, and speaker, like:

    [t0042 @ 0:12:33 | Dana Lee] Let's require SSO through the corporate identity provider.

Read the whole brief and output knowledge items as a JSON array.

# What counts as a knowledge item

Durable facts that would belong in a specification or rules document: decisions,
business rules, requirements, constraints, scope inclusions/exclusions, defined
behaviors, policies, and confirmed answers to open questions. Each item must be a
**single, self-contained, declarative statement** — not a quote, not a paraphrase
of chit-chat.

Do NOT emit: greetings, scheduling, opinions-in-passing, status updates, tangents,
or anything you could not write into a spec. Precision over volume. A 60-minute
meeting might yield 3–15 real items; that is fine.

# Style of the `statement`

Write it like a rules document, present tense, declarative, standalone:
- GOOD: "Users authenticate via SSO through the corporate identity provider."
- GOOD: "Refund requests must be submitted within 30 days of purchase."
- BAD:  "Dana said they'd probably use SSO for login I think."

Fold status into the item via the `status` field (not the statement). If a thing
was explicitly deferred or out of scope, say so and set status accordingly.

# Categories

Group each item under a category. {{CATEGORY_GUIDANCE}}

# Output schema — JSON array, nothing else

```json
[
  {
    "category": "Authentication & Access",
    "statement": "Users authenticate via SSO through the corporate identity provider.",
    "status": "confirmed",                // confirmed|tentative|draft|pending|deferred|superseded
    "note": null,                          // short qualifier, e.g. "pending stakeholder confirmation"
    "related": [],                         // optional cross-references you are confident about
    "supersedes": [],                      // ids/statements this replaces, if any
    "sources": [
      {
        "meeting": "{{MEETING}}",
        "date": "{{DATE}}",
        "speaker": "Dana Lee",
        "timestamp": "0:12:33",
        "quote": "Let's require SSO through the corporate identity provider.",
        "turn_id": "t0042"
      }
    ]
  }
]
```

# Hard rules

1. Output ONLY the JSON array. No prose, no code fence commentary.
2. Every item MUST have at least one source with a real `turn_id` copied from the
   brief and a short `quote` of the supporting words. No item without provenance.
3. Never invent a turn id, speaker, or quote. If you cannot cite it, drop it.
4. Prefer one well-worded item with several sources over many duplicates.

# Transcript brief

{{BRIEF}}

# Output

Return the JSON array now.
