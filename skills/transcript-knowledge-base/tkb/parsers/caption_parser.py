"""WebVTT (.vtt) and SubRip (.srt) caption parsers.

Caption files carry strong timing data but speaker attribution is optional. VTT
supports ``<v Alice>`` voice tags and ``Alice: text`` cue prefixes; SRT usually
only has numbered cues with timecodes. We extract whatever speaker hints exist
and always keep the timestamps, which feed provenance timestamp ranges.
"""

from __future__ import annotations

import re

from .base import RawTranscript, RawTurn, register

_VTT_TIME = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{1,2}:\d{2}[.,]\d{3})"
)
_VOICE_TAG = re.compile(r"<v\s+(?P<speaker>[^>]+)>(?P<text>.*?)(?:</v>|$)", re.S)
_SPEAKER_PREFIX = re.compile(r"^(?P<speaker>[A-Z0-9][\w .'\-]{0,40}?):\s*(?P<text>.+)$")
_TAG_STRIP = re.compile(r"<[^>]+>")


def _parse_cues(content: str) -> list[RawTurn]:
    turns: list[RawTurn] = []
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        start = end = None
        text_lines: list[str] = []
        for ln in lines:
            tm = _VTT_TIME.search(ln)
            if tm:
                start, end = tm.group("start"), tm.group("end")
                continue
            # Skip cue numbers / WEBVTT header / NOTE lines.
            if ln.strip().isdigit() or ln.strip().upper().startswith(("WEBVTT", "NOTE")):
                continue
            text_lines.append(ln.strip())
        if not text_lines:
            continue
        raw_text = " ".join(text_lines)

        speaker = None
        vm = _VOICE_TAG.search(raw_text)
        if vm:
            speaker = vm.group("speaker").strip()
            raw_text = vm.group("text")
        else:
            pm = _SPEAKER_PREFIX.match(raw_text)
            if pm and start is not None:
                speaker = pm.group("speaker").strip()
                raw_text = pm.group("text")
        text = _TAG_STRIP.sub("", raw_text).strip()
        if not text:
            continue
        turns.append(RawTurn(speaker=speaker, text=text, start_time=start, end_time=end))
    return turns


def _merge_consecutive(turns: list[RawTurn]) -> list[RawTurn]:
    """Merge adjacent cues from the same (or unknown) speaker into utterances.

    Captions fragment a sentence across many short cues; merging restores
    turn-level granularity that downstream chunking/extraction expect.
    """
    merged: list[RawTurn] = []
    for t in turns:
        if merged and merged[-1].speaker == t.speaker:
            merged[-1].text = (merged[-1].text + " " + t.text).strip()
            merged[-1].end_time = t.end_time or merged[-1].end_time
        else:
            merged.append(RawTurn(speaker=t.speaker, text=t.text, start_time=t.start_time, end_time=t.end_time))
    return merged


@register(".vtt", ".srt")
def parse(path: str, content: str) -> RawTranscript:
    turns = _merge_consecutive(_parse_cues(content))
    seen: dict[str, None] = {}
    for t in turns:
        if t.speaker:
            seen.setdefault(t.speaker, None)
    warnings = [] if turns else ["no cues parsed from caption file"]
    return RawTranscript(turns=turns, participants=list(seen.keys()), warnings=warnings)
