from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

MEMORY_TYPES = ("user", "feedback", "project", "reference", "insight", "chat")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_LINK_RE = re.compile(r"\[\[([a-zA-Z0-9_-]+)\]\]")


@dataclass
class Note:
    name: str
    description: str
    type: str
    body: str
    path: Path | None = None
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())

    def links(self) -> list[str]:
        return _LINK_RE.findall(self.body)

    def to_markdown(self) -> str:
        frontmatter = (
            f"---\n"
            f"name: {self.name}\n"
            f"description: {self.description}\n"
            f"metadata:\n"
            f"  type: {self.type}\n"
            f"  updated: {self.updated}\n"
            f"---\n\n"
        )
        return frontmatter + self.body.strip() + "\n"

    @classmethod
    def from_markdown(cls, text: str, path: Path | None = None) -> "Note":
        m = _FRONTMATTER_RE.match(text)
        if not m:
            raise ValueError(f"no frontmatter block found in {path or '<string>'}")
        header, body = m.groups()
        fields: dict[str, str] = {}
        note_type = "reference"
        updated = None
        for line in header.splitlines():
            line = line.strip()
            if line.startswith("type:"):
                note_type = line.split(":", 1)[1].strip()
            elif line.startswith("updated:"):
                updated = line.split(":", 1)[1].strip()
            elif ":" in line and not line.startswith(" "):
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
        kwargs = dict(
            name=fields.get("name", path.stem if path else "unknown"),
            description=fields.get("description", ""),
            type=note_type,
            body=body.strip(),
            path=path,
        )
        if updated:
            kwargs["updated"] = updated
        return cls(**kwargs)


PERSONA_HEADER = """# Persona

Patterns noticed over time, meant to be read by you as much as by any agent
using goldfish — open this file directly any time (`goldfish persona`, or
just open it in an editor). The goal is that, given enough real sessions,
it eventually surfaces something about your own patterns you hadn't
consciously noticed yourself.

Nothing here is a diagnosis. Each entry below traces back to real cited
moments (session + line, verifiable via goldfish_search or brain_get) and is
one tentative reading of them, not a verdict — entries are meant to be
revisited and pruned as they age, not treated as permanent truth. An agent
may also draw on this at its own discretion to shape how it responds to you,
but rarely — it's a reference, not a script for narrating you back to
yourself.
"""


class MemoryStore:
    """A directory of Note files plus two generated aggregate views.

    Layout matches the convention already used by hand: one markdown file per
    note (frontmatter + body), a flat MEMORY.md index of one-line pointers
    across every type, and PERSONA.md — the same idea specialized to
    type="insight" notes, but holding each one's full body rather than a
    one-liner, since that's the file meant to accumulate a real picture of
    the user over time rather than just point at where to look.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "MEMORY.md"
        self.persona_path = self.root / "PERSONA.md"

    def _slug_path(self, name: str) -> Path:
        return self.root / f"{name}.md"

    def write(self, note: Note) -> Path:
        if note.type not in MEMORY_TYPES:
            raise ValueError(f"type must be one of {MEMORY_TYPES}, got {note.type!r}")
        path = self._slug_path(note.name)
        path.write_text(note.to_markdown())
        self._rebuild_index()
        self._rebuild_persona()
        return path

    def read(self, name: str) -> Note:
        path = self._slug_path(name)
        if not path.exists():
            raise FileNotFoundError(f"no memory named {name!r} in {self.root}")
        return Note.from_markdown(path.read_text(), path=path)

    def delete(self, name: str) -> bool:
        path = self._slug_path(name)
        if not path.exists():
            return False
        path.unlink()
        self._rebuild_index()
        self._rebuild_persona()
        return True

    def list(self, type: str | None = None) -> list[Note]:
        notes = []
        for path in sorted(self.root.glob("*.md")):
            if path.name in ("MEMORY.md", "PERSONA.md"):
                continue
            try:
                note = Note.from_markdown(path.read_text(), path=path)
            except ValueError:
                continue
            if type is None or note.type == type:
                notes.append(note)
        return notes

    def search(self, query: str) -> list[Note]:
        q = query.lower()
        return [
            n for n in self.list()
            if q in n.name.lower() or q in n.description.lower() or q in n.body.lower()
        ]

    def _rebuild_index(self) -> None:
        lines = ["# Memory index", ""]
        for note in self.list():
            lines.append(f"- [{note.name}]({note.path.name}) — {note.description}")
        self.index_path.write_text("\n".join(lines) + "\n")

    def _rebuild_persona(self) -> None:
        insights = self.list(type="insight")
        lines = [PERSONA_HEADER]
        if not insights:
            lines.append("_Nothing recorded yet — see goldfish_reflect._")
        for note in insights:
            lines.append(f"## {note.name}")
            lines.append(f"*{note.description}* — updated {note.updated}")
            lines.append("")
            lines.append(note.body)
            lines.append("")
        self.persona_path.write_text("\n".join(lines).rstrip() + "\n")
