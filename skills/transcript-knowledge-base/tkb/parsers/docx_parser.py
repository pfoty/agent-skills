"""Microsoft Word (.docx) transcript parser — the primary format for Copilot /
Microsoft Teams meeting-recording exports.

A .docx is a zip of XML, so this needs no third-party package: we read
``word/document.xml`` with the standard library and pull text per paragraph.

These exports come in three observed shapes, all handled by one state machine:

1. **Legend + multi-paragraph** — a "Speaker 1: Jason Voivich" legend at the top,
   then the body as separate paragraphs: a ``Speaker 1`` label, a timestamp line,
   an ``@1 ...`` annotation, then the spoken text.
2. **Inline with speaker** — one paragraph per turn:
   ``Nathan Kaskarli   0:11Hey, guys. Good morning.``
3. **Inline without speaker** — diarization off:
   ``0:02On the vendor side and some of the more technical things.``

We map ``Speaker N`` labels to real names via the legend, capture timestamps for
provenance, read the meeting date from the header line or the filename, and strip
the private-use icon glyphs and "AI-generated content may be incorrect" noise that
Teams injects.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
import zipfile

from .base import ParseError, RawTranscript, RawTurn, register

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# One paragraph per turn: optional "Name   " then a m:ss / h:mm:ss stamp, then text.
_INLINE = re.compile(
    r"^(?:(?P<speaker>[A-Za-z][\w .,'&\-]*?)\s{2,})?"
    r"(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)"
    r"(?P<text>.+)$"
)
# A standalone timestamp/duration line (multi-paragraph layout).
_TS_ONLY = re.compile(
    r"^(?:\d+\s*minutes?\s*\d+\s*seconds?)?\s*\d{1,2}:\d{2}(?::\d{2})?$"
    r"|^\d+\s*minutes?\s*\d+\s*seconds?$",
    re.IGNORECASE,
)
_TS_GRAB = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?)")
_SPEAKER_LABEL = re.compile(r"^Speaker\s+\d+$", re.IGNORECASE)
_LEGEND = re.compile(r"^(Speaker\s+\d+)\s*:\s*(.+)$", re.IGNORECASE)
_DURATION_HEADER = re.compile(r"^\d+\s*m\s*\d+\s*s$", re.IGNORECASE)
_DATE_HEADER = re.compile(
    r"^[A-Z][a-z]+ \d{1,2}, \d{4}(?:,?\s+\d{1,2}:\d{2}\s*[AP]M)?", re.IGNORECASE
)
_PUA = re.compile(r"[-]")  # Teams icon glyphs

_NOISE_PREFIXES = (
    "ai-generated content may be incorrect",
    "general mapping of speakers",
)
_NOISE_CONTAINS = ("started transcription", "stopped transcription")


def _read_paragraphs(path: str) -> list[str]:
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                raise ParseError("docx has no word/document.xml")
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except zipfile.BadZipFile as exc:
        raise ParseError(f"not a valid .docx (zip) file: {exc}") from exc

    root = ET.fromstring(xml)
    paras: list[str] = []
    for p in root.iter(_W + "p"):
        parts: list[str] = []
        for node in p.iter():
            if node.tag == _W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == _W + "tab":
                parts.append(" ")
        line = "".join(parts)
        if line.strip():
            paras.append(line)
    return paras


def _clean(line: str) -> str:
    return _PUA.sub("", line).strip()


def _is_noise(line: str) -> bool:
    low = line.lower()
    if line.startswith("@"):
        return True
    if any(low.startswith(p) for p in _NOISE_PREFIXES):
        return True
    if any(c in low for c in _NOISE_CONTAINS):
        return True
    if _DURATION_HEADER.match(line):
        return True
    return False


@register(".docx")
def parse(path: str, content: str = "") -> RawTranscript:
    # ``content`` is ignored: docx is binary, so we read the file directly.
    paras = [_clean(p) for p in _read_paragraphs(path)]
    paras = [p for p in paras if p]

    speaker_map: dict[str, str] = {}
    conversation_date: str | None = None
    title: str | None = None
    warnings: list[str] = []

    turns: list[RawTurn] = []
    cur_speaker: str | None = None
    pending_ts: str | None = None
    new_segment = True

    for i, line in enumerate(paras):
        # Legend: "Speaker 1: Jason Voivich"
        m = _LEGEND.match(line)
        if m:
            speaker_map[m.group(1).strip().lower()] = m.group(2).strip()
            continue

        # Header date line, e.g. "January 28, 2026, 4:30PM"
        if conversation_date is None and _DATE_HEADER.match(line):
            conversation_date = _to_iso_date(line)
            continue

        # First non-noise line is typically the meeting title.
        if title is None and not _is_noise(line) and not _INLINE.match(line) \
                and not _TS_ONLY.match(line) and not _SPEAKER_LABEL.match(line):
            title = line
            continue

        if _is_noise(line):
            continue

        # Standalone speaker label ("Speaker 3") -> resolve via legend.
        if _SPEAKER_LABEL.match(line):
            cur_speaker = speaker_map.get(line.lower(), line)
            new_segment = True
            continue

        # Standalone timestamp / duration line.
        if _TS_ONLY.match(line):
            g = _TS_GRAB.search(line)
            if g:
                pending_ts = g.group(1)
            new_segment = True
            continue

        # Inline "Name   0:11text" or "0:02text".
        inline = _INLINE.match(line)
        if inline and inline.group("text").strip():
            sp = inline.group("speaker")
            if sp:
                sp = sp.strip()
                cur_speaker = speaker_map.get(sp.lower(), sp)
            turns.append(
                RawTurn(
                    speaker=cur_speaker,
                    text=inline.group("text").strip(),
                    start_time=inline.group("ts"),
                )
            )
            new_segment = False
            continue

        # Plain spoken text (multi-paragraph layout): start a turn at a segment
        # boundary, otherwise continue the current turn.
        if new_segment or not turns:
            turns.append(RawTurn(speaker=cur_speaker, text=line, start_time=pending_ts))
            new_segment = False
        else:
            turns[-1].text = (turns[-1].text + " " + line).strip()

    if title is None:
        title = os.path.splitext(os.path.basename(path))[0]
    if conversation_date is None:
        conversation_date = _date_from_filename(os.path.basename(path))
    if not turns:
        warnings.append("no turns parsed from docx transcript")

    participants = list(dict.fromkeys(speaker_map.values())) or _speakers_from_turns(turns)

    return RawTranscript(
        turns=turns,
        title=title,
        conversation_date=conversation_date,
        participants=participants,
        language="en",
        source_system="microsoft_teams",
        warnings=warnings,
    )


def _speakers_from_turns(turns: list[RawTurn]) -> list[str]:
    seen: dict[str, None] = {}
    for t in turns:
        if t.speaker:
            seen.setdefault(t.speaker, None)
    return list(seen.keys())


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _to_iso_date(line: str) -> str | None:
    m = re.match(r"^([A-Za-z]+) (\d{1,2}), (\d{4})", line)
    if m:
        mon = _MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"
    return None


def _date_from_filename(name: str) -> str | None:
    # 20260128_163018 or 20260115 -> YYYY-MM-DD
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # _1.28.26 / 4.1.26 / 12.5.2025 -> M.D.YY(YY)
    m = re.search(r"[_\s](\d{1,2})\.(\d{1,2})\.(\d{2,4})", name)
    if m:
        mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        yr = yr + 2000 if yr < 100 else yr
        if 1 <= mo <= 12 and 1 <= da <= 31:
            return f"{yr:04d}-{mo:02d}-{da:02d}"
    # "Jan 12 2026" / "Dec 1 2025"
    m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})\s+(20\d{2})", name)
    if m:
        mon = _MONTHS.get(m.group(1)[:3].lower())
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"
    return None
