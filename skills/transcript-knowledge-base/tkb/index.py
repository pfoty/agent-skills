"""The knowledge index: a curated, categorized set of knowledge items, each with
provenance, persisted as a markdown document plus a small JSON state sidecar.

This replaces the old SQLite/heuristic pipeline. The deliverable is the markdown
file (``knowledge-index.md``); the JSON (``knowledge-index.state.json``) is a
lightweight, regenerable cache that lets incremental runs merge new transcripts
into existing rules without re-reading old ones. It is intentionally *not* a
database — just a file you can read, diff, or delete.

The shape mirrors a hand-curated business-rules document:

    ## <Category>
    | ID | Rule | Sources |
    | CAT-1 | <canonical statement, status folded inline> | <meeting (date)…> |

    ## Evidence
    ### CAT-1
    > "<verbatim quote>" — <speaker>, *<meeting>* (<date>) @ <timestamp>

The mechanical concerns live here (id assignment, dedup/merge, rendering). The
*synthesis* — turning raw dialogue into clean canonical rules — is done by the
agent running the skill (see SKILL.md); this module just stores and renders what
the agent produces, and guarantees every item keeps its provenance.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from .utils import now_iso, keywords, jaccard

# Statuses recognized; anything other than "confirmed" is surfaced inline on the
# rule, the way a curated doc flags drafts and out-of-scope items.
STATUSES = ("confirmed", "tentative", "draft", "pending", "deferred", "superseded")


@dataclass
class Source:
    """Provenance for one knowledge item — where the rule came from."""

    meeting: str
    date: Optional[str] = None
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    quote: Optional[str] = None
    file: Optional[str] = None
    turn_id: Optional[str] = None

    def key(self) -> tuple:
        # Identity for dedup across runs.
        return (self.meeting or "", self.timestamp or "", (self.quote or "")[:80])


@dataclass
class KnowledgeItem:
    id: str
    category: str
    statement: str
    status: str = "confirmed"
    note: Optional[str] = None
    related: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)

    def validate(self) -> list[str]:
        errs = []
        if not self.statement.strip():
            errs.append("empty statement")
        if not self.sources:
            errs.append("no provenance (sources empty)")  # the cardinal rule
        if self.status not in STATUSES:
            errs.append(f"unknown status {self.status!r}")
        return errs


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def derive_prefix(category: str) -> str:
    """A stable id prefix from a category name, e.g. 'Bidding' -> 'BID'."""
    words = re.findall(r"[A-Za-z]+", category)
    if not words:
        return "GEN"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:4]).upper()


class KnowledgeIndex:
    """Load / merge / render the knowledge index."""

    def __init__(
        self,
        title: str = "Knowledge Index",
        intro: str = "",
        dedup_threshold: float = 0.6,
    ):
        self.title = title
        self.intro = intro
        self.dedup_threshold = dedup_threshold
        self.items: dict[str, KnowledgeItem] = {}
        self.category_order: list[str] = []
        self.prefixes: dict[str, str] = {}          # category -> id prefix
        self.ingested_files: dict[str, dict] = {}    # file_path -> {hash,name,date}
        self.generated_at: Optional[str] = None
        # Cache of each item's dedup keyword set so duplicate detection doesn't
        # recompute keywords for every existing item on every merge (that was an
        # O(n^2) hot spot that hurt at thousands of items). Keyed by item id.
        self._kw_cache: dict[str, set[str]] = {}

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, state_path: str) -> "KnowledgeIndex":
        import os
        idx = cls()
        if not os.path.exists(state_path):
            return idx
        with open(state_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        idx.title = data.get("title", idx.title)
        idx.intro = data.get("intro", idx.intro)
        idx.dedup_threshold = data.get("dedup_threshold", idx.dedup_threshold)
        idx.category_order = data.get("category_order", [])
        idx.prefixes = data.get("prefixes", {})
        idx.ingested_files = data.get("ingested_files", {})
        idx.generated_at = data.get("generated_at")
        for raw in data.get("items", []):
            srcs = [Source(**s) for s in raw.pop("sources", [])]
            idx.items[raw["id"]] = KnowledgeItem(sources=srcs, **raw)
        return idx

    def save(self, state_path: str) -> None:
        data = {
            "title": self.title,
            "intro": self.intro,
            "dedup_threshold": self.dedup_threshold,
            "generated_at": self.generated_at,
            "category_order": self.category_order,
            "prefixes": self.prefixes,
            "ingested_files": self.ingested_files,
            "items": [
                {**{k: v for k, v in asdict(it).items() if k != "sources"},
                 "sources": [asdict(s) for s in it.sources]}
                for it in self.items.values()
            ],
        }
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # Category & id management
    # ------------------------------------------------------------------ #
    def ensure_category(self, category: str, prefix: Optional[str] = None) -> str:
        if category not in self.category_order:
            self.category_order.append(category)
        if category not in self.prefixes:
            self.prefixes[category] = prefix or self._unique_prefix(category)
        return self.prefixes[category]

    def _unique_prefix(self, category: str) -> str:
        base = derive_prefix(category)
        used = set(self.prefixes.values())
        if base not in used:
            return base
        i = 2
        while f"{base}{i}" in used:
            i += 1
        return f"{base}{i}"

    def _next_id(self, category: str) -> str:
        prefix = self.prefixes[category]
        nums = [
            int(m.group(1))
            for it in self.items.values()
            if it.category == category
            for m in [re.match(rf"^{re.escape(prefix)}-(\d+)$", it.id)]
            if m
        ]
        return f"{prefix}-{(max(nums) + 1) if nums else 1}"

    # ------------------------------------------------------------------ #
    # Merge
    # ------------------------------------------------------------------ #
    def merge_item(
        self,
        category: str,
        statement: str,
        sources: list[Source],
        status: str = "confirmed",
        note: Optional[str] = None,
        related: Optional[list[str]] = None,
        supersedes: Optional[list[str]] = None,
        prefix: Optional[str] = None,
    ) -> tuple[str, bool]:
        """Add a new item or fold it into an existing near-duplicate.

        Returns (item_id, created). When an existing item in the same category is
        similar enough, the new sources/links are appended to it (never losing the
        prior evidence) and its statement may be upgraded to the more recent one.
        """
        self.ensure_category(category, prefix)
        # An explicit supersedes marks the referenced item(s) superseded — the
        # newer conversation replaced an earlier assumption. Evidence is kept.
        self._apply_supersession(supersedes)

        target_kw = _dedup_keywords(statement)
        match = self._find_duplicate(category, target_kw)
        if match is not None:
            self._fold_into(match, statement, sources, status, note, related, supersedes)
            self._kw_cache[match.id] = _dedup_keywords(match.statement)  # statement may have grown
            return match.id, False

        new_id = self._next_id(category)
        item = KnowledgeItem(
            id=new_id, category=category, statement=statement.strip(),
            status=status if status in STATUSES else "confirmed", note=note,
            related=list(related or []), supersedes=list(supersedes or []),
            sources=list(sources),
        )
        self.items[new_id] = item
        self._kw_cache[new_id] = target_kw
        return new_id, True

    def _apply_supersession(self, supersedes: Optional[list[str]]) -> None:
        for sid in supersedes or []:
            target = self.items.get(sid)
            if target is not None and target.status != "superseded":
                target.status = "superseded"

    def _find_duplicate(self, category: str, target_kw: set[str]) -> Optional[KnowledgeItem]:
        best, best_sim = None, 0.0
        for it in self.items.values():
            if it.category != category:
                continue
            kw = self._kw_cache.get(it.id)
            if kw is None:  # lazily populate (e.g. after load())
                kw = _dedup_keywords(it.statement)
                self._kw_cache[it.id] = kw
            sim = jaccard(target_kw, kw)
            if sim > best_sim:
                best, best_sim = it, sim
        return best if best_sim >= self.dedup_threshold else None

    @staticmethod
    def _fold_into(item, statement, sources, status, note, related, supersedes):
        existing = {s.key() for s in item.sources}
        for s in sources:
            if s.key() not in existing:
                item.sources.append(s)
                existing.add(s.key())
        for r in (related or []):
            if r not in item.related:
                item.related.append(r)
        for sp in (supersedes or []):
            if sp not in item.supersedes:
                item.supersedes.append(sp)
        # A later "superseded"/"deferred" signal wins; otherwise keep prior status
        # unless the incoming one is more definitive (confirmed beats tentative).
        rank = {s: i for i, s in enumerate(STATUSES)}
        if status in ("superseded", "deferred", "draft", "pending"):
            item.status = status
        elif rank.get(status, 99) < rank.get(item.status, 99):
            item.status = status
        if note and not item.note:
            item.note = note
        # Prefer the longer, presumably more complete statement.
        if len(statement.strip()) > len(item.statement):
            item.statement = statement.strip()

    def mark_ingested(self, file_path: str, content_hash: str, name: str, date: Optional[str]) -> None:
        self.ingested_files[file_path] = {"hash": content_hash, "name": name, "date": date}

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def render_markdown(self) -> str:
        self.generated_at = now_iso()
        out: list[str] = [f"# {self.title}", ""]
        if self.intro:
            out += [self.intro, ""]
        out += [
            f"_Generated {self.generated_at[:10]} from "
            f"{len(self.ingested_files)} transcript(s); "
            f"{len(self.items)} knowledge items across {len(self.category_order)} categories._",
            "",
            "Each item cites the meeting(s), date, and speaker(s) it came from. The full "
            "verbatim quotes and timestamps are retained in the state file (queryable, "
            "kept out of this document so it stays compact as the corpus grows).",
            "",
            "---",
            "",
        ]

        for category in self.category_order:
            items = [it for it in self.items.values() if it.category == category]
            if not items:
                continue
            items.sort(key=_id_sort_key)
            out += [f"## {category}", "", "| ID | Rule | Sources |", "|----|------|---------|"]
            for it in items:
                out.append(f"| {it.id} | {self._rule_cell(it)} | {self._sources_cell(it)} |")
            out.append("")

        return "\n".join(out).rstrip() + "\n"

    def _rule_cell(self, it: KnowledgeItem) -> str:
        text = _md_cell(it.statement)
        annot = []
        if it.status and it.status != "confirmed":
            label = it.status.capitalize()
            annot.append(f"{label}{(' — ' + it.note) if it.note else ''}")
        elif it.note:
            annot.append(it.note)
        if it.supersedes:
            annot.append("supersedes " + ", ".join(it.supersedes))
        if it.related:
            annot.append("see " + ", ".join(it.related))
        if annot:
            text += " _(" + "; ".join(_md_cell(a) for a in annot) + ")_"
        return text

    @staticmethod
    def _sources_cell(it: KnowledgeItem) -> str:
        """Compact provenance: meeting (date; speakers), one entry per meeting.

        The verbatim quote/timestamp live in the state file; the rendered cell
        stays short so the document scales with the corpus.
        """
        groups: dict[tuple, list[str]] = {}
        order: list[tuple] = []
        for s in it.sources:
            key = (s.meeting, s.date)
            if key not in groups:
                groups[key] = []
                order.append(key)
            if s.speaker and s.speaker not in groups[key]:
                groups[key].append(s.speaker)

        parts = []
        for meeting, date in order:
            inner = []
            if date:
                inner.append(date)
            if groups[(meeting, date)]:
                inner.append(", ".join(groups[(meeting, date)]))
            label = meeting + (f" ({'; '.join(inner)})" if inner else "")
            parts.append(_md_cell(label))
        return "; ".join(parts)


def _dedup_keywords(statement: str) -> set[str]:
    """Keyword set for duplicate detection, with light plural normalization so
    'bids'/'bid' and 'amounts'/'amount' don't count as different rules."""
    out: set[str] = set()
    for w in keywords(statement, limit=25):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def _md_cell(text: str) -> str:
    """Escape a value for inline use inside a markdown table cell."""
    text = " ".join((text or "").split())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _id_sort_key(it: KnowledgeItem):
    m = re.match(r"^([A-Za-z]+)-?(\d+)$", it.id)
    return (m.group(1), int(m.group(2))) if m else (it.id, 0)
