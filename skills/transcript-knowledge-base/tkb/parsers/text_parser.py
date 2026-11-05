"""Plain-text and Markdown transcript parser.

Handles the common shapes seen in exported meeting notes:

    [00:01:02] Alice: Let's start.
    Alice (00:01:02): Let's start.
    Alice: Let's start.
    > a line with no speaker continues the previous turn

A leading ``# Title`` Markdown heading or ``Title:``/``Date:`` metadata lines at
the top are captured as conversation metadata. Lines with no recognizable speaker
are appended to the current turn so prose-style transcripts still ingest cleanly.
"""

from __future__ import annotations

import re

from .base import RawTranscript, RawTurn, register

# [hh:mm:ss] or [mm:ss] optionally with milliseconds, anywhere a timestamp leads.
_TS = r"(?P<ts>\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?)"
_SPEAKER = r"(?P<speaker>[A-Z0-9][\w .'\-]{0,40}?)"

_PATTERNS = [
    # [00:01:02] Alice: text
    re.compile(rf"^\s*\[{_TS}\]\s*{_SPEAKER}\s*:\s*(?P<text>.*)$"),
    # Alice (00:01:02): text
    re.compile(rf"^\s*{_SPEAKER}\s*\({_TS}\)\s*:\s*(?P<text>.*)$"),
    # 00:01:02 Alice: text
    re.compile(rf"^\s*{_TS}\s+{_SPEAKER}\s*:\s*(?P<text>.*)$"),
    # Alice: text  (no timestamp)
    re.compile(rf"^\s*{_SPEAKER}\s*:\s*(?P<text>.*)$"),
]

_META_RE = re.compile(r"^(?P<key>title|date|participants|language)\s*:\s*(?P<val>.+)$", re.I)


@register(".txt", ".md")
def parse(path: str, content: str) -> RawTranscript:
    title = None
    conversation_date = None
    participants: list[str] = []
    language = None
    turns: list[RawTurn] = []
    warnings: list[str] = []

    lines = content.splitlines()
    body_started = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Markdown title heading (only before any turn).
        if not body_started and line.lstrip().startswith("#"):
            heading = line.lstrip("#").strip()
            if heading and title is None:
                title = heading
            continue

        # Metadata key: value lines, only in the header region.
        if not body_started:
            m = _META_RE.match(line.strip())
            if m:
                key = m.group("key").lower()
                val = m.group("val").strip()
                if key == "title":
                    title = val
                elif key == "date":
                    conversation_date = val
                elif key == "participants":
                    participants = [p.strip() for p in re.split(r"[,;]", val) if p.strip()]
                elif key == "language":
                    language = val
                continue

        matched = False
        for pat in _PATTERNS:
            m = pat.match(line)
            if m:
                body_started = True
                gd = m.groupdict()
                ts = gd.get("ts")
                turns.append(
                    RawTurn(
                        speaker=(gd.get("speaker") or "").strip() or None,
                        text=gd.get("text", "").strip(),
                        start_time=ts,
                    )
                )
                matched = True
                break

        if not matched:
            # Continuation of the previous turn, or untagged prose.
            if turns:
                body_started = True
                if turns[-1].text:
                    turns[-1].text += " " + line.strip()
                else:
                    turns[-1].text = line.strip()
            else:
                # No speaker yet: treat as a single anonymous narration turn.
                turns.append(RawTurn(speaker=None, text=line.strip()))
                body_started = True

    # Derive participants from speakers if not declared.
    if not participants:
        seen: dict[str, None] = {}
        for t in turns:
            if t.speaker:
                seen.setdefault(t.speaker, None)
        participants = list(seen.keys())

    if not turns:
        warnings.append("no turns parsed from text transcript")

    return RawTranscript(
        turns=turns,
        title=title,
        conversation_date=conversation_date,
        participants=participants,
        language=language,
        warnings=warnings,
    )
