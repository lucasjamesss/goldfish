"""Goldfish MCP server — one set of tools over three memory tiers:

  goldfish_search    -> brain (full transcript history, cited file+line+sha256)
  goldfish_context   -> claude-mem (recent session-compression summaries)
  goldfish_remember  -> memory_notes (write a curated, durable note)
  goldfish_recall    -> memory_notes (read/search curated notes)
  goldfish_save_chat -> memory_notes (conversation summary, for chat apps
                        that keep no transcripts on disk)
  goldfish_reflect   -> brain (raw cited evidence of the user's own recurring
                        language — frustration, habit, drive, goal talk —
                        never a synthesized conclusion; see its docstring)
  goldfish_persona   -> memory_notes (PERSONA.md — every insight note
                        accumulated so far, as one evolving document)
  goldfish_status    -> health across all three backends

brain-mcp and claude-mem each remain independently installable and useful; this
server does not replace them, it gives a caller one place to ask "what do we
know" without deciding up front which tier holds the answer.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer

from . import config
from . import context_bridge
from memory_notes import MemoryStore, Note

mcp = MCPServer(
    "goldfish",
    title="goldfish — unified memory",
    instructions=(
        "One MCP server over three memory tiers for AI coding agents: "
        "goldfish_search (brain-mcp: full cited transcript history), "
        "goldfish_context (claude-mem: recent session-compression summaries), "
        "goldfish_remember/goldfish_recall (memory_notes: curated durable facts). "
        "\n\n"
        "Persona evaluation — entirely at your own discretion, never required: "
        "goldfish_reflect gathers raw cited evidence of the user's own recurring "
        "language (frustration, habit, drive, goal talk); it never concludes "
        "anything itself. If a real pattern holds up across multiple genuine "
        "citations, you may write it via goldfish_remember(type='insight', ...) — "
        "phrased as tentative noticing anchored to evidence, never diagnosis. "
        "goldfish_persona reads back everything accumulated this way so far as "
        "one evolving document — over time it can end up holding patterns the "
        "user has never explicitly named themselves. You decide, in each moment, "
        "whether drawing on it would genuinely improve your response or help the "
        "user — the way a good long-term collaborator notices things without "
        "narrating them. When you do use it, keep it rare, well-placed, and tied "
        "to real evidence; never a running commentary on who the user is. "
        "\n\n"
        "goldfish_status reports which backends are actually installed and healthy."
        "\n\n"
        "Chat apps (e.g. Claude Desktop's chat, any plan including free) don't "
        "write transcripts to disk, so brain has nothing to search there. In that "
        "case goldfish is the only memory: at the start of a conversation call "
        "goldfish_recall (no args) to see what's known, save lasting facts with "
        "goldfish_remember as they come up, and before a meaningful conversation "
        "ends call goldfish_save_chat with a short summary so goldfish_search can "
        "find it later."
    ),
)

_store = MemoryStore(config.memory_home())


@mcp.tool(title="Search full transcript history (cited or abstained)",
          annotations={"readOnlyHint": True})
def goldfish_search(query: str, agent: Optional[str] = None, limit: int = 10) -> dict[str, Any]:
    """Search full AI conversation history (Claude Code, Codex, etc.) via brain-mcp.

    Every result is a citation (file, line span, sha256) verifiable with the
    underlying brain-mcp toolset — never a synthesized/paraphrased claim.

    Also matches saved notes (including goldfish_save_chat summaries) under
    "notes" — the only history available to chat apps that keep no transcripts.
    """
    try:
        brain_api = _brain_api()
        result = brain_api.search(query, agent=agent, limit=limit)
    except Exception as e:  # noqa: BLE001 - no brain data must not hide note matches
        result = {"error": f"transcript search unavailable: {e}"}
    notes = _search_notes(query, limit)
    if notes:
        result["notes"] = notes
    return result


def _brain_api():
    """brain's API, or RuntimeError when there's no transcript DB to read.

    Chat-app-only installs (Claude Desktop) never create the DB, and brain's
    read path waits up to 90s on a missing file as if it were locked.
    """
    try:
        from brain_mcp.recorder import api as brain_api
        from brain_mcp.recorder.paths import db_path
    except ImportError:
        raise RuntimeError("brain-mcp not installed — see packages/brain in the goldfish repo")
    if not db_path().exists():
        raise RuntimeError("no transcript history on this machine (only Claude Code / Codex sessions are recorded)")
    return brain_api


def _search_notes(query: str, limit: int) -> list[dict[str, Any]]:
    """Notes containing every word of the query, newest first."""
    words = query.lower().split()
    hits = []
    for n in _store.list():
        text = f"{n.name} {n.description} {n.body}".lower()
        if words and all(w in text for w in words):
            hits.append(n)
    hits.sort(key=lambda n: n.updated, reverse=True)
    return [{"name": n.name, "type": n.type, "description": n.description,
             "updated": n.updated, "body": n.body} for n in hits[:limit]]


@mcp.tool(title="Recent session-compression summaries", annotations={"readOnlyHint": True})
def goldfish_context(limit: int = 5) -> dict[str, Any]:
    """Recent session-compression summaries from claude-mem, if installed."""
    db = config.claude_mem_db()
    if not context_bridge.is_available(db):
        return {"available": False, "reason": f"no claude-mem database at {db}"}
    return {"available": True, "summaries": context_bridge.recent_session_summaries(db, limit=limit)}


@mcp.tool(title="Write a curated, durable memory note")
def goldfish_remember(name: str, description: str, type: str, content: str) -> dict[str, Any]:
    """Write a curated, durable memory note (user/feedback/project/reference/insight).

    Use this for facts worth carrying into future sessions — not for raw
    transcript (that's captured automatically by brain) or session summaries
    (that's claude-mem's job) — only hand-picked, still-true facts.

    type="insight" is for tentative, evidence-linked pattern observations about
    the user (see goldfish_reflect) — distinct from type="user" (settled facts)
    because insights are interpretive and should be revisited/pruned over time,
    not treated as permanent truth.
    """
    note = Note(name=name, description=description, type=type, body=content)
    path = _store.write(note)
    return {"written": str(path)}


@mcp.tool(title="Save a summary of this conversation")
def goldfish_save_chat(title: str, summary: str) -> dict[str, Any]:
    """Save a summary of the current conversation so future chats can find it.

    For chat apps that don't record transcripts (e.g. Claude Desktop chat).
    Call it before a meaningful conversation ends, or when the user asks to
    save/remember this chat. `summary` should cover what was discussed,
    decided, and left to do — enough to pick the thread back up later.
    Coding agents with transcript capture (Claude Code, Codex) don't need it.
    """
    now = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "chat"
    name = f"chat-{now:%Y%m%d-%H%M%S}-{slug}"
    note = Note(name=name, description=title.replace("\n", " "), type="chat", body=summary)
    path = _store.write(note)
    return {"written": str(path), "name": name}


@mcp.tool(title="Read or search curated memory notes", annotations={"readOnlyHint": True})
def goldfish_recall(name: Optional[str] = None, query: Optional[str] = None, type: Optional[str] = None) -> dict[str, Any]:
    """Read a curated memory note by name, or search/list curated notes."""
    if name:
        try:
            note = _store.read(name)
        except FileNotFoundError as e:
            return {"error": str(e)}
        return {"name": note.name, "description": note.description, "type": note.type, "body": note.body}
    if query:
        notes = _store.search(query)
    else:
        notes = _store.list(type=type)
    return {"notes": [{"name": n.name, "description": n.description, "type": n.type} for n in notes]}


DEFAULT_REFLECTION_QUERIES = [
    "frustrated", "annoying", "I hate when", "why does this keep happening",
    "I always", "I never", "every time I", "I keep",
    "should have", "I need to", "burnt out", "overwhelmed", "tired of",
    "excited about", "proud of", "love this",
]


@mcp.tool(title="Gather raw cited evidence of the user's own recurring language",
          annotations={"readOnlyHint": True})
def goldfish_reflect(focus: Optional[str] = None, limit_per_query: int = 5) -> dict[str, Any]:
    """Evidence for behavioral/preference patterns — never this tool's own conclusion.

    Searches role='user' only (their words, not the agent's) across full transcript
    history via brain. Pass `focus` for one specific angle (e.g. "decisions I keep
    reversing"); omit it to run a default battery covering frustration, habit, drive,
    and goal language.

    This tool does not diagnose, summarize, or conclude anything about the user —
    it hands back excerpts with citations, same as goldfish_search. Turning that
    into an actual observation — and judging whether it's even worth keeping — is
    the calling agent's job. If a real pattern shows up across multiple citations,
    write it with goldfish_remember(type="insight", ...), phrased as tentative
    pattern-noticing anchored to the evidence, never as a firm psychological claim.
    Mention it in conversation rarely, only when it's genuinely useful in the
    moment — this is not a running personality commentary.
    """
    try:
        brain_api = _brain_api()
    except RuntimeError as e:
        return {"error": str(e)}

    queries = [focus] if focus else DEFAULT_REFLECTION_QUERIES
    results = []
    for q in queries:
        hits = brain_api.search(q, role="user", limit=limit_per_query)
        if not hits.get("abstained"):
            results.append({"query": q, "hits": hits.get("hits", [])})
    return {
        "note": "raw cited evidence only — pattern synthesis is the calling agent's job, not this tool's",
        "queries_run": len(queries),
        "queries_with_hits": len(results),
        "results": results,
    }


@mcp.tool(title="Persona evaluation — everything learned about the user so far",
          annotations={"readOnlyHint": True})
def goldfish_persona() -> dict[str, Any]:
    """The cumulative persona file: every insight note, aggregated into one document.

    Entirely optional and at your own discretion — nothing requires you to
    call this or to use what it returns. It exists so a capable agent can
    occasionally draw on real, evidence-linked patterns about the user built
    up over goldfish_reflect calls over time — to shape tone, or catch
    something worth mentioning — the way a good long-term collaborator would.

    Every entry traces back to cited evidence (see goldfish_reflect); nothing
    here is a diagnosis, and entries are meant to be revisited as they age,
    not treated as permanent truth. Use judgment about whether and when
    surfacing something from this file actually helps the user in the
    moment — this is not a mandate to comment on who they are.
    """
    if not _store.persona_path.exists():
        return {"available": False, "reason": "no persona notes recorded yet — see goldfish_reflect"}
    content = _store.persona_path.read_text()
    insight_count = len(_store.list(type="insight"))
    return {"available": True, "insight_count": insight_count, "content": content}


@mcp.tool(title="Health across all three memory tiers", annotations={"readOnlyHint": True})
def goldfish_status() -> dict[str, Any]:
    """Health summary across all three memory tiers."""
    status: dict[str, Any] = {}

    try:
        status["brain"] = _brain_api().health()
    except Exception as e:  # noqa: BLE001 - surface any backend failure as status, not a crash
        status["brain"] = {"ok": False, "error": str(e)}

    db = config.claude_mem_db()
    status["claude_mem"] = {"ok": context_bridge.is_available(db), "db_path": str(db)}

    notes = _store.list()
    status["memory_notes"] = {"ok": True, "count": len(notes), "root": str(_store.root)}
    status["persona"] = {
        "insight_count": len(_store.list(type="insight")),
        "path": str(_store.persona_path),
    }

    return status


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
