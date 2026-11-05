"""CSV transcript parser.

Expects a header row. Columns are matched case-insensitively against common
names for speaker / text / start / end / timestamp. A single ``timestamp`` column
is used as the start time when no explicit start/end columns exist.
"""

from __future__ import annotations

import csv
import io

from .base import ParseError, RawTranscript, RawTurn, register

_SPEAKER_COLS = ("speaker", "name", "author", "from", "participant", "role")
_TEXT_COLS = ("text", "utterance", "content", "message", "transcript", "dialogue")
_START_COLS = ("start", "start_time", "begin", "timestamp", "time", "ts")
_END_COLS = ("end", "end_time", "stop")


def _find_col(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    lower = {f.lower().strip(): f for f in fieldnames}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


@register(".csv")
def parse(path: str, content: str) -> RawTranscript:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ParseError("CSV has no header row")

    text_col = _find_col(reader.fieldnames, _TEXT_COLS)
    if text_col is None:
        raise ParseError(f"CSV has no recognizable text column (looked for {_TEXT_COLS})")
    speaker_col = _find_col(reader.fieldnames, _SPEAKER_COLS)
    start_col = _find_col(reader.fieldnames, _START_COLS)
    end_col = _find_col(reader.fieldnames, _END_COLS)

    turns: list[RawTurn] = []
    warnings: list[str] = []
    for i, row in enumerate(reader):
        text = (row.get(text_col) or "").strip()
        if not text:
            warnings.append(f"row {i} had empty text; skipped")
            continue
        turns.append(
            RawTurn(
                speaker=(row.get(speaker_col).strip() if speaker_col and row.get(speaker_col) else None),
                text=text,
                start_time=(row.get(start_col).strip() if start_col and row.get(start_col) else None),
                end_time=(row.get(end_col).strip() if end_col and row.get(end_col) else None),
            )
        )

    seen: dict[str, None] = {}
    for t in turns:
        if t.speaker:
            seen.setdefault(t.speaker, None)
    return RawTranscript(turns=turns, participants=list(seen.keys()), warnings=warnings)
