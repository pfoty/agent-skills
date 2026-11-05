"""Tests for the knowledge index: id assignment, dedup/merge, provenance, render."""

import unittest

from helpers import ROOT, temp_dir  # noqa: F401

from tkb.index import KnowledgeIndex, Source, derive_prefix


def src(meeting="Kickoff", date="2026-01-05", speaker="Maya", ts="0:12", quote="...", turn="t0001"):
    return Source(meeting=meeting, date=date, speaker=speaker, timestamp=ts, quote=quote, turn_id=turn)


class TestIndexMerge(unittest.TestCase):
    def test_ids_assigned_per_category(self):
        idx = KnowledgeIndex()
        i1, new1 = idx.merge_item("Bidding", "Bids must be whole dollars.", [src()])
        i2, new2 = idx.merge_item("Bidding", "All bidding is blind to other bidders.", [src()])
        i3, _ = idx.merge_item("Authentication & Access", "Users authenticate via SSO.", [src()])
        self.assertEqual((i1, i2), ("BID-1", "BID-2"))
        self.assertTrue(i3.startswith("AA"))  # derived prefix from two words
        self.assertTrue(new1 and new2)

    def test_near_duplicate_merges_and_keeps_all_sources(self):
        idx = KnowledgeIndex()
        a, _ = idx.merge_item("Bidding", "Bid amounts must be a positive multiple of the minimum bid.",
                              [src(meeting="Scope Discussion", quote="multiple of the minimum")])
        b, created = idx.merge_item("Bidding", "Bids must be a positive multiple of the minimum bid amount.",
                                    [src(meeting="Standup", date="2026-01-28", quote="multiple of minimum bid")])
        self.assertEqual(a, b)            # folded into the same item
        self.assertFalse(created)
        item = idx.items[a]
        self.assertEqual(len(item.sources), 2)   # both meetings retained as evidence
        meetings = {s.meeting for s in item.sources}
        self.assertEqual(meetings, {"Scope Discussion", "Standup"})

    def test_unrelated_statements_do_not_merge(self):
        idx = KnowledgeIndex()
        idx.merge_item("Bidding", "All bidding is blind to other bidders.", [src()])
        _id, created = idx.merge_item("Bidding", "Pickup penalties apply after a grace period.", [src()])
        self.assertTrue(created)
        self.assertEqual(len(idx.items), 2)

    def test_supersession_marks_referenced_item(self):
        idx = KnowledgeIndex()
        old, _ = idx.merge_item("Auction", "Auctions launch in March.", [src(date="2026-01-05")],
                                status="tentative")
        new, _ = idx.merge_item("Auction", "Auctions launch in April per revised plan.",
                                [src(date="2026-02-02")], status="confirmed", supersedes=[old])
        # The newer item explicitly supersedes the older; the old one is marked,
        # but its evidence is preserved (not deleted).
        self.assertEqual(idx.items[old].status, "superseded")
        self.assertEqual(idx.items[new].status, "confirmed")
        self.assertTrue(idx.items[old].sources)

    def test_provenance_is_mandatory(self):
        idx = KnowledgeIndex()
        item = idx.items.get(idx.merge_item("X", "A rule.", [src()])[0])
        self.assertEqual(item.validate(), [])
        item.sources = []
        self.assertIn("no provenance (sources empty)", item.validate())


class TestRender(unittest.TestCase):
    def _idx(self):
        idx = KnowledgeIndex(title="Acme Rules", intro="Rules from discovery.")
        idx.merge_item("Authentication & Access", "Users authenticate via SSO through Acme ID.",
                       [src(meeting="Alignment", date="2026-01-15", speaker="Jason",
                            ts="0:12:04", quote="we go through Acme ID for sign on", turn="t0042")],
                       prefix="AUTH")
        idx.merge_item("Bidding", "All bidding is blind; bidders cannot see other bids.",
                       [src(meeting="Scope", date="2026-01-21", quote="bidding is blind")],
                       prefix="BID", status="confirmed")
        return idx

    def test_markdown_structure(self):
        md = self._idx().render_markdown()
        self.assertIn("# Acme Rules", md)
        self.assertIn("## Authentication & Access", md)
        self.assertIn("| ID | Rule | Sources |", md)
        self.assertIn("| AUTH-1 |", md)
        self.assertIn("Users authenticate via SSO through Acme ID.", md)
        # Provenance is in the sources cell: meeting (date; speaker).
        self.assertIn("Alignment (2026-01-15; Jason)", md)
        # The verbatim appendix is intentionally NOT rendered (kept in state).
        self.assertNotIn("## Evidence", md)
        self.assertNotIn("we go through Acme ID for sign on", md)

    def test_verbatim_quote_retained_in_state_not_in_markdown(self):
        import os
        idx = self._idx()
        md = idx.render_markdown()
        self.assertNotIn("0:12:04", md)               # timestamp not in the doc
        d = temp_dir()
        state = os.path.join(d, "s.json")
        idx.save(state)
        reloaded = KnowledgeIndex.load(state)
        # ...but the full quote + timestamp survive in the state file.
        src = reloaded.items["AUTH-1"].sources[0]
        self.assertEqual(src.quote, "we go through Acme ID for sign on")
        self.assertEqual(src.timestamp, "0:12:04")

    def test_status_folded_inline(self):
        idx = KnowledgeIndex()
        idx.merge_item("Scope", "Buy Now is deferred to a future phase.",
                       [src(quote="buy now later")], status="deferred", note="not Phase 1")
        md = idx.render_markdown()
        self.assertIn("Deferred", md)
        self.assertIn("not Phase 1", md)

    def test_table_cell_escaping(self):
        idx = KnowledgeIndex()
        idx.merge_item("X", "A rule with a | pipe and a break.", [src()])
        md = idx.render_markdown()
        self.assertIn("\\|", md)  # pipe escaped so the table is not broken

    def test_round_trip_state(self):
        import os
        idx = self._idx()
        d = temp_dir()
        state = os.path.join(d, "state.json")
        idx.save(state)
        idx2 = KnowledgeIndex.load(state)
        self.assertEqual(len(idx2.items), 2)
        self.assertEqual(idx2.items["AUTH-1"].sources[0].quote, "we go through Acme ID for sign on")


class TestPrefix(unittest.TestCase):
    def test_derive_prefix(self):
        self.assertEqual(derive_prefix("Bidding"), "BID")
        self.assertEqual(derive_prefix("Authentication & Access"), "AA")
        self.assertEqual(derive_prefix("Terms & Conditions"), "TC")


if __name__ == "__main__":
    unittest.main()
