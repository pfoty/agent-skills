"""End-to-end demonstration of the knowledge-index workflow.

Shows the full lifecycle on small sample transcripts:

1. prepare  — scan a folder, write citation-tagged briefs for new transcripts
2. merge    — fold (simulated) extracted items into the index (dedup + provenance)
3. render   — write the knowledge-index.md deliverable
4. incremental — add a transcript, re-run; only the new file is prepared, and a
   restated rule folds into the existing item as a second source (no duplicate)

In real use, step 2's items come from the agent reading the briefs (see SKILL.md).
Here we hand-write them so the demo runs with no LLM.
"""

from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tkb.config import Config            # noqa: E402
from tkb.index import KnowledgeIndex, Source  # noqa: E402
from tkb import prepare as P             # noqa: E402

KICKOFF = (
    "Title: Project Kickoff\nDate: 2026-01-05\n\n"
    "[00:00:05] Maya: We decided users authenticate via SSO through the IN portal.\n"
    "[00:00:30] Devin: A bid must be a positive multiple of the minimum bid amount.\n"
)
REVIEW = (
    "Title: Review\nDate: 2026-02-02\n\n"
    "[00:00:05] Priya: Confirming again, users authenticate via SSO through the IN portal.\n"
    "[00:00:30] Devin: All bidding is blind; bidders cannot see other bidders' bids.\n"
)


def banner(t):
    print("\n" + "=" * 68 + f"\n{t}\n" + "=" * 68)


def main():
    work = tempfile.mkdtemp(prefix="tkb_demo_")
    folder = os.path.join(work, "transcripts")
    os.makedirs(folder)
    state = os.path.join(work, "index.state.json")
    out = os.path.join(work, "knowledge-index.md")
    cfg = Config()

    def save(idx):
        idx.save(state)

    # 1. initial transcript
    open(os.path.join(folder, "kickoff.txt"), "w", encoding="utf-8").write(KICKOFF)

    banner("STEP 1 - prepare (scan + briefs)")
    idx = KnowledgeIndex.load(state)
    manifest = P.prepare(folder, cfg, idx, os.path.join(work, "briefs"))
    print("to_process:", [f["name"] for f in manifest["files"]])

    banner("STEP 2 - merge extracted items (with provenance)")
    f = manifest["files"][0]
    idx.merge_item("Authentication", "Users authenticate via SSO through the IN portal.",
                   [Source("Project Kickoff", "2026-01-05", "Maya", "00:00:05",
                           "authenticate via SSO through the IN portal", f["name"], "t0000")], prefix="AUTH")
    idx.merge_item("Bidding", "A bid must be a positive multiple of the minimum bid amount.",
                   [Source("Project Kickoff", "2026-01-05", "Devin", "00:00:30",
                           "positive multiple of the minimum bid", f["name"], "t0001")], prefix="BID")
    idx.mark_ingested(f["path"], f["hash"], f["name"], f["date"])
    save(idx)
    print("items:", len(idx.items))

    banner("STEP 3 - render the deliverable")
    open(out, "w", encoding="utf-8").write(idx.render_markdown())
    save(idx)
    print("wrote", out)

    banner("STEP 4 - incremental: add a transcript, re-run")
    open(os.path.join(folder, "review.txt"), "w", encoding="utf-8").write(REVIEW)
    idx = KnowledgeIndex.load(state)
    manifest2 = P.prepare(folder, cfg, idx, os.path.join(work, "briefs"))
    print("only prepared:", [f["name"] for f in manifest2["files"]])
    print("skipped unchanged:", manifest2["unchanged"])

    f2 = manifest2["files"][0]
    # A restatement of AUTH-1 -> folds in as a second source, not a new id.
    before = len(idx.items["AUTH-1"].sources)
    idx.merge_item("Authentication", "Users authenticate via SSO through the IN portal.",
                   [Source("Review", "2026-02-02", "Priya", "00:00:05",
                           "users authenticate via SSO", f2["name"], "t0000")], prefix="AUTH")
    # A genuinely new rule.
    idx.merge_item("Bidding", "All bidding is blind; bidders cannot see other bidders' bids.",
                   [Source("Review", "2026-02-02", "Devin", "00:00:30",
                           "bidding is blind", f2["name"], "t0001")], prefix="BID")
    idx.mark_ingested(f2["path"], f2["hash"], f2["name"], f2["date"])
    save(idx)
    print(f"AUTH-1 sources: {before} -> {len(idx.items['AUTH-1'].sources)} (merged, not duplicated)")
    print("total items:", len(idx.items))

    open(out, "w", encoding="utf-8").write(idx.render_markdown())
    print("\nFinal index:", out)
    print("\n--- first 20 lines ---")
    print("\n".join(open(out, encoding="utf-8").read().splitlines()[:20]))


if __name__ == "__main__":
    main()
