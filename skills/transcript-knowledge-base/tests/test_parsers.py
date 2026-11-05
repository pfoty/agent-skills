"""Parser unit tests across formats, including malformed input."""

import unittest

from helpers import ROOT  # noqa: F401  (sets up sys.path)

from tkb.parsers import parse_file, ParseError
from tkb.parsers.text_parser import parse as parse_text
from tkb.parsers.json_parser import parse as parse_json
from tkb.parsers.caption_parser import parse as parse_caption
from tkb.parsers.csv_parser import parse as parse_csv


class TestTextParser(unittest.TestCase):
    def test_timestamped_speaker_lines(self):
        txt = "# My Meeting\nDate: 2026-01-05\n[00:01:02] Alice: Hello there.\nBob: Hi Alice."
        r = parse_text("x.txt", txt)
        self.assertEqual(r.title, "My Meeting")
        self.assertEqual(r.conversation_date, "2026-01-05")
        self.assertEqual(len(r.turns), 2)
        self.assertEqual(r.turns[0].speaker, "Alice")
        self.assertEqual(r.turns[0].start_time, "00:01:02")
        self.assertEqual(r.turns[1].speaker, "Bob")
        self.assertIn("Alice", r.participants)

    def test_continuation_lines_merge(self):
        txt = "Alice: first part\nsecond part continues"
        r = parse_text("x.txt", txt)
        self.assertEqual(len(r.turns), 1)
        self.assertIn("second part", r.turns[0].text)

    def test_prose_without_speakers_still_ingests(self):
        r = parse_text("x.txt", "just some narration with no speaker labels")
        self.assertEqual(len(r.turns), 1)
        self.assertIsNone(r.turns[0].speaker)


class TestJsonParser(unittest.TestCase):
    def test_object_with_turns(self):
        data = '{"title":"T","participants":["A"],"turns":[{"speaker":"A","text":"hi","start":"0:01"}]}'
        r = parse_json("x.json", data)
        self.assertEqual(r.title, "T")
        self.assertEqual(r.turns[0].speaker, "A")
        self.assertEqual(r.turns[0].start_time, "0:01")

    def test_list_of_turns_and_alt_keys(self):
        data = '[{"name":"A","content":"hello"},{"author":"B","message":"world"}]'
        r = parse_json("x.json", data)
        self.assertEqual(len(r.turns), 2)
        self.assertEqual(r.turns[1].speaker, "B")
        self.assertEqual(r.turns[1].text, "world")

    def test_invalid_json_raises(self):
        with self.assertRaises(ParseError):
            parse_json("x.json", "{not json")

    def test_object_without_turns_raises(self):
        with self.assertRaises(ParseError):
            parse_json("x.json", '{"foo": 1}')


class TestCaptionParser(unittest.TestCase):
    def test_vtt_voice_tags_and_merge(self):
        vtt = (
            "WEBVTT\n\n"
            "1\n00:00:01.000 --> 00:00:03.000\n<v Alice>Hello</v>\n\n"
            "2\n00:00:03.500 --> 00:00:05.000\n<v Alice>again</v>\n\n"
            "3\n00:00:05.500 --> 00:00:07.000\n<v Bob>Hi</v>\n"
        )
        r = parse_caption("x.vtt", vtt)
        # Two consecutive Alice cues merge into one turn.
        self.assertEqual(len(r.turns), 2)
        self.assertEqual(r.turns[0].speaker, "Alice")
        self.assertIn("Hello", r.turns[0].text)
        self.assertIn("again", r.turns[0].text)
        self.assertEqual(r.turns[0].start_time, "00:00:01.000")

    def test_srt_without_speakers(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\nNo speaker here\n"
        r = parse_caption("x.srt", srt)
        self.assertEqual(len(r.turns), 1)
        self.assertIsNone(r.turns[0].speaker)


class TestCsvParser(unittest.TestCase):
    def test_columns_detected(self):
        csv_text = "speaker,timestamp,text\nAlice,00:01,hello\nBob,00:02,world\n"
        r = parse_csv("x.csv", csv_text)
        self.assertEqual(len(r.turns), 2)
        self.assertEqual(r.turns[0].speaker, "Alice")
        self.assertEqual(r.turns[0].start_time, "00:01")

    def test_missing_text_column_raises(self):
        with self.assertRaises(ParseError):
            parse_csv("x.csv", "speaker,foo\nAlice,bar\n")


if __name__ == "__main__":
    unittest.main()
