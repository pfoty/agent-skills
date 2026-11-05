"""Tests for prepare: discovery, change detection, briefs, incremental skipping."""

import os
import time
import unittest

from helpers import ROOT, temp_dir, write  # noqa: F401

from tkb.config import Config
from tkb.index import KnowledgeIndex
from tkb import prepare as P

KICKOFF = (
    "Title: Kickoff\nDate: 2026-01-05\n\n"
    "[00:00:05] Maya: We decided to go with the EU-first rollout.\n"
    "[00:00:30] Devin: I'll draft the compliance plan by 2026-01-19.\n"
)


class TestPrepare(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.join(temp_dir(), "t")
        os.makedirs(self.folder)
        self.work = os.path.join(self.folder, "..", "work")
        self.cfg = Config()
        self.idx = KnowledgeIndex()

    def test_build_brief_tags_turns(self):
        path = write(self.folder, "k.txt", KICKOFF)
        info = P.build_brief(path)
        self.assertEqual(info["meeting"], "Kickoff")
        self.assertEqual(info["date"], "2026-01-05")
        self.assertIn("[t0000 @ 00:00:05 | Maya]", info["brief"])
        self.assertIn("EU-first rollout", info["brief"])

    def test_classify_new_changed_unchanged(self):
        write(self.folder, "a.txt", KICKOFF)
        write(self.folder, "b.txt", KICKOFF + "Maya: One more thing.\n")
        disc = P.discover(self.folder, self.cfg)
        # First time: both new.
        c = P.classify(self.idx, disc)
        self.assertEqual(len(c["new"]), 2)
        self.assertEqual(len(c["unchanged"]), 0)
        # Mark one ingested; reclassify -> that one is unchanged.
        a = next(d for d in disc if d.name == "a.txt")
        self.idx.mark_ingested(a.path, a.content_hash, a.name, "2026-01-05")
        c2 = P.classify(self.idx, P.discover(self.folder, self.cfg))
        self.assertEqual({d.name for d in c2["unchanged"]}, {"a.txt"})
        self.assertEqual({d.name for d in c2["new"]}, {"b.txt"})

    def test_changed_file_detected_by_hash(self):
        a = write(self.folder, "a.txt", KICKOFF)
        disc = P.discover(self.folder, self.cfg)[0]
        self.idx.mark_ingested(disc.path, disc.content_hash, disc.name, "2026-01-05")
        time.sleep(0.01)
        write(self.folder, "a.txt", KICKOFF + "Maya: Actually, launch in April.\n")
        c = P.classify(self.idx, P.discover(self.folder, self.cfg))
        self.assertEqual({d.name for d in c["changed"]}, {"a.txt"})

    def test_prepare_writes_briefs_and_manifest(self):
        write(self.folder, "a.txt", KICKOFF)
        manifest = P.prepare(self.folder, self.cfg, self.idx, self.work)
        self.assertEqual(manifest["counts"]["to_process"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.work, "_manifest.json")))
        self.assertTrue(os.path.exists(manifest["files"][0]["brief_path"]))
        self.assertIn("hash", manifest["files"][0])

    def test_malformed_file_reported_not_crashing(self):
        write(self.folder, "good.txt", KICKOFF)
        write(self.folder, "bad.json", "{not valid json")
        manifest = P.prepare(self.folder, self.cfg, self.idx, self.work)
        names = {f["name"]: f for f in manifest["files"]}
        self.assertIn("error", names["bad.json"])
        self.assertNotIn("error", names["good.txt"])


if __name__ == "__main__":
    unittest.main()
