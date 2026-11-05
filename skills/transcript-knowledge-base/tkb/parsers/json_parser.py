"""JSON transcript parser.

Accepts the formats most transcription tools emit. It is deliberately tolerant
about field names because there is no single standard:

Top level may be either a list of turns or an object with metadata plus a turns
array under one of: ``turns``, ``utterances``, ``messages``, ``segments``,
``transcript``, ``entries``.

Per-turn speaker keys tried: ``speaker``, ``speaker_name``, ``name``, ``author``,
``role``, ``from``. Text keys: ``text``, ``content``, ``message``, ``body``,
``value``. Time keys: ``start``/``start_time``/``ts``/``begin`` and
``end``/``end_time``/``stop``.
"""

from __future__ import annotations

import json
from typing import Any

from .base import ParseError, RawTranscript, RawTurn, register

_TURN_CONTAINERS = ("turns", "utterances", "messages", "segments", "transcript", "entries")
_SPEAKER_KEYS = ("speaker", "speaker_name", "name", "author", "role", "from")
_TEXT_KEYS = ("text", "content", "message", "body", "value")
_START_KEYS = ("start", "start_time", "ts", "begin", "startTime")
_END_KEYS = ("end", "end_time", "stop", "endTime")


def _first(d: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


@register(".json")
def parse(path: str, content: str) -> RawTranscript:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ParseError(f"invalid JSON: {exc}") from exc

    meta: dict[str, Any] = {}
    if isinstance(data, list):
        raw_turns = data
    elif isinstance(data, dict):
        meta = data
        raw_turns = None
        for key in _TURN_CONTAINERS:
            if isinstance(data.get(key), list):
                raw_turns = data[key]
                break
        if raw_turns is None:
            raise ParseError(
                "JSON object has no recognizable turns array "
                f"(looked for {_TURN_CONTAINERS})"
            )
    else:
        raise ParseError("JSON root must be a list or object")

    turns: list[RawTurn] = []
    warnings: list[str] = []
    for i, item in enumerate(raw_turns):
        if isinstance(item, str):
            turns.append(RawTurn(speaker=None, text=item))
            continue
        if not isinstance(item, dict):
            warnings.append(f"skipped non-object turn at index {i}")
            continue
        text = _first(item, _TEXT_KEYS)
        if text is None:
            warnings.append(f"turn {i} had no text field; skipped")
            continue
        speaker = _first(item, _SPEAKER_KEYS)
        turns.append(
            RawTurn(
                speaker=str(speaker) if speaker is not None else None,
                text=str(text).strip(),
                start_time=_coerce_time(_first(item, _START_KEYS)),
                end_time=_coerce_time(_first(item, _END_KEYS)),
            )
        )

    participants = meta.get("participants") or meta.get("speakers")
    if isinstance(participants, str):
        participants = [participants]
    if not participants:
        seen: dict[str, None] = {}
        for t in turns:
            if t.speaker:
                seen.setdefault(t.speaker, None)
        participants = list(seen.keys())

    return RawTranscript(
        turns=turns,
        title=meta.get("title") or meta.get("name"),
        conversation_date=meta.get("date") or meta.get("conversation_date") or meta.get("started_at"),
        participants=list(participants),
        language=meta.get("language") or meta.get("lang"),
        source_system=meta.get("source") or meta.get("source_system") or meta.get("platform"),
        warnings=warnings,
    )


def _coerce_time(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
