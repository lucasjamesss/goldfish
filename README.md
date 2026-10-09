# 🐠 Goldfish

## Start here (non-technical)

**Easiest:** open Claude Code and paste this:

> Install goldfish for me from https://github.com/lucasjamesss/goldfish. Run its install.sh, then confirm it worked by running goldfish_status.

**Or by hand (Mac, with the Claude app opened once):** open Terminal (Cmd+Space, type "Terminal"), paste the install command from [Install](#install), press Enter, then quit Claude (Cmd+Q) and reopen it.

**Check it worked:** in a new chat, ask "Run goldfish_status." Each tier should report healthy or tell you what is missing.

**Where your data lives:** on your computer only. Curated notes are plain markdown files in `~/.goldfish/memory`. Nothing is uploaded by goldfish. Whatever you ask Claude to save goes into those files, so don't ask it to save passwords or card numbers.

**Platforms:** macOS is supported. Linux works for Claude Code. Windows is not supported yet.

**Remove it:** `bash ~/.local/share/goldfish/uninstall.sh`. This unregisters goldfish and removes the install. Your notes and history are never deleted.

---

Unified memory for AI coding agents. One MCP server, three tiers, no more
guessing which tool remembers what:

```
                    ┌──────────────────────┐
   your agent  ───► │   goldfish (MCP)     │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────────┐
        ▼                      ▼                           ▼
┌───────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  brain         │     │  claude-mem         │     │  memory_notes      │
│  full history  │     │  session context    │     │  curated facts     │
│  cited search  │     │  auto-compressed    │     │  hand-written      │
│  (vendored)    │     │  (vendored)         │     │  (new)             │
└───────────────┘     └────────────────────┘     └──────────────────┘
```

Three different jobs, three different tools, one thing you actually call:

| Tier | Tool | What it answers | Backing store |
|---|---|---|---|
| Transcript history | `goldfish_search` | "did we ever discuss X" — cited, never hallucinated | [brain-mcp](https://github.com/mordechaipotash/brain-mcp)'s DuckDB + append-only JSONL lake |
| Session context | `goldfish_context` | "what was I just doing" — recent auto-generated summaries | [claude-mem](https://github.com/thedotmack/claude-mem)'s SQLite store (read-only) |
| Curated notes | `goldfish_remember` / `goldfish_recall` | "what do we know about this user/project" — small, hand-picked, durable | plain frontmatter markdown, this repo |
| Chat summaries | `goldfish_save_chat` | "what did we talk about last week" in chat apps that keep no transcripts on disk | same markdown store, `type: chat` |
| Everything | `goldfish_status` | is each tier actually installed and healthy | aggregates all three |

Goldfish doesn't replace brain-mcp or claude-mem — it vendors them as-is and
gives you one server to point an agent at instead of three. See
[ATTRIBUTION.md](ATTRIBUTION.md) for full upstream credit and licenses.

## Noticing patterns (optional, and deliberately hands-off)

Goldfish can also help notice your own recurring patterns over time —
frustrations, habits, stated drives, things you keep saying you should do
more or less of. The goal is that file is worth reading yourself: given
enough real sessions, it should eventually surface something about your own
patterns you hadn't consciously put together before. An agent using goldfish
can also draw on it, when it's genuinely relevant, to let that shape how it
talks to you — but you reading it directly is just as much the point as any
AI doing so. This isn't a hidden feature; here's exactly how it works and
where the line is:

- `goldfish_reflect` pulls raw, cited excerpts of things **you've** said
  (`role="user"` only — never the agent's own words) across your full
  history. It runs a small default battery of angles (frustration, habit,
  drive, goal language), or one specific `focus` you give it.
- It never concludes anything itself — no keyword-matched "you seem
  stressed" heuristics. Turning evidence into an actual observation is left
  to whichever LLM is using the tool, because that's the only part of this
  that requires real judgment.
- If a pattern holds up across real evidence, the agent can write it with
  `goldfish_remember(type="insight", ...)` — a note type distinct from plain
  `user` facts specifically because insights are interpretive and should be
  revisited over time, not treated as settled truth.
- Every `insight` note also gets folded into **`PERSONA.md`**, one evolving,
  plain-English document that accumulates everything noticed this way.
  `goldfish_persona` reads it back in one call for an agent — but it's just a
  markdown file at `~/.goldfish/memory/PERSONA.md`, so open it yourself
  whenever you want (`uv run goldfish persona` prints it straight to your
  terminal). That's exactly why it's held to a higher bar than a plain fact:
  tentative, cited, and meant to be pruned as it ages, never treated as a
  verdict — it has to be worth *you* reading, not just an agent.
- Whether and when to draw on any of this — `goldfish_reflect`,
  `goldfish_persona`, or an `insight` note — is left entirely to the calling
  agent's judgment. The server's own instructions say so explicitly: rare,
  well-placed, tied to real evidence, never a running commentary on who you
  are. Nothing here is forced into every response.
- Everything stays local. `PERSONA.md` and every `insight` note live in the
  same `memory_notes` store as everything else (`~/.goldfish/memory` by
  default) — never inside this repo, never committed, never sent anywhere.
  `goldfish_reflect` only ever runs when an agent decides to call it; there's
  no background job scanning your history for this.

Don't want this at all? Just don't use `goldfish_reflect`, `goldfish_persona`,
or `type="insight"` — everything else works exactly the same without it.

## Install

Paste this repo's link to Claude Code and say "use this" — it'll run the
installer itself. Or run it yourself:

```bash
curl -fsSL https://raw.githubusercontent.com/lucasjamesss/goldfish/v0.1.0/install.sh | GOLDFISH_REF=v0.1.0 bash
```

That command is pinned to release `v0.1.0`, a fixed version that later edits to this repo can't change. It clones goldfish, syncs its Python env, and registers it with
every Claude client it finds — restart Claude afterward and the tools are live.
Re-running it is safe (idempotent).

- **Claude Code:** turns on brain-mcp's transcript-capture hooks and runs
  `claude mcp add`. Full cited history search works.
- **Claude desktop app (any plan, free included):** merges goldfish into
  `claude_desktop_config.json` (old file backed up as `.json.bak`). The chat
  app keeps no transcripts on disk, so memory there is what Claude saves:
  facts via `goldfish_remember`, conversation summaries via
  `goldfish_save_chat`, both found again by `goldfish_search`. The installer
  prints a line to paste into Settings > Profile so Claude does this every chat.

### Handing it to a friend who doesn't code

They need a Mac with the Claude app installed and opened once. Have them open
Terminal (Cmd+Space, type "Terminal"), paste the command above, press Enter,
then quit Claude (Cmd+Q) and reopen it. That's it.

Prefer to wire it up by hand instead? See [manual setup](#manual-setup) below.

claude-mem's own hooks/worker aren't installed by the script — that's a
separate project with its own setup. `goldfish_context` just reads its
database read-only if you've already installed it yourself; see
`packages/claude-mem/README.md`.

## Manual setup

```bash
git clone --branch v0.1.0 https://github.com/lucasjamesss/goldfish.git
cd goldfish
uv sync
uv run --directory packages/brain brain-mcp install cc   # optional: transcript capture hooks
claude mcp add goldfish -s user -- uv run --directory "$(pwd)" goldfish serve
```

Or hand-edit your MCP config (e.g. `~/.claude.json` or a project `.mcp.json`):

```json
{
  "mcpServers": {
    "goldfish": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/goldfish", "goldfish", "serve"]
    }
  }
}
```

## CLI

```bash
uv run goldfish status                                    # health across all 3 tiers
uv run goldfish remember my-note "one-liner" --type project --content "..."
uv run goldfish recall --query "my-note"
uv run goldfish reflect --focus "decisions I keep reversing"   # raw cited evidence, no synthesis
uv run goldfish persona                                        # print the accumulated PERSONA.md
```

## Repo layout

```
goldfish/
├── goldfish/          # the unifying MCP server + CLI (new)
├── memory_notes/       # curated-note store: frontmatter .md + index (new)
├── packages/
│   ├── brain/          # vendored from mordechaipotash/brain-mcp (MIT)
│   └── claude-mem/      # vendored from thedotmack/claude-mem (Apache-2.0)
├── ATTRIBUTION.md
└── LICENSE              # MIT, covers goldfish/ + memory_notes/ only
```

## Roadmap

Rough priority order, none of this started yet unless marked:

- [x] One-command install (`install.sh` — clone, sync, hooks, `claude mcp add`)
- [ ] `install.sh` also registers goldfish for Codex (`~/.codex/config.toml`), not just Claude Code
- [x] `uninstall.sh` — clean removal (hooks, scheduler, Claude Code + desktop registration); notes and history are kept
- [ ] `goldfish uninstall` as a CLI subcommand, so it works without the script
- [ ] Package goldfish as an installable Claude Code plugin (marketplace `.mcp.json` + `hooks.json`) instead of raw MCP config editing
- [ ] Optional claude-mem auto-install path in `install.sh`, for people who want `goldfish_context` populated out of the box
- [ ] `goldfish_remember` commits `memory_notes/` to a local git repo automatically, so curated notes get real version history
- [ ] Semantic (embedding) search over curated notes and recent context, not just brain's BM25 over raw transcript
- [ ] Surface brain's other capture lanes (Cursor, ChatGPT, Pi) through `goldfish_status` more prominently — the data's already there, just under-exposed
- [ ] A small local dashboard to browse all three tiers side by side, for people who don't want to think in tool calls
- [x] `goldfish_reflect` + `type="insight"` — cited evidence of the user's own recurring language, synthesized only by the calling agent, surfaced rarely and only in-context
- [ ] Let `goldfish_reflect` run on an opt-in schedule instead of only when an agent calls it (still local-only, still no auto-surfacing)
- [ ] Auto-expire or flag stale `insight` notes so pattern-observations don't calcify into permanent "truth"

Have an idea or a use case this doesn't cover? Open an issue.

## Why

Most setups end up with two or three memory tools installed for different
reasons (a transcript recorder, a session-compression plugin, some markdown
notes) and no single place to ask "what do we know." Goldfish is that single
place — a thin, honest layer on top of tools that already do the hard parts
well.
