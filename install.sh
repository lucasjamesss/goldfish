#!/usr/bin/env bash
# Goldfish one-command installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lucasjamesss/goldfish/master/install.sh | bash
#
# Idempotent — safe to re-run. Clones/updates goldfish, syncs its Python env,
# then registers goldfish with whichever Claude clients are installed:
#   - Claude Code: transcript-capture hooks (brain-mcp) + `claude mcp add`
#   - Claude Desktop (any plan, including free): its claude_desktop_config.json

set -euo pipefail

REPO_URL="https://github.com/lucasjamesss/goldfish.git"
INSTALL_DIR="${GOLDFISH_HOME:-$HOME/.local/share/goldfish}"
# Optional: pin to a tag or branch, e.g. GOLDFISH_REF=v0.1.0 (default: master).
REF="${GOLDFISH_REF:-}"

echo "== Goldfish installer =="
cat <<'INFO'
This will:
  1. Download goldfish to ~/.local/share/goldfish (or the folder in GOLDFISH_HOME)
  2. Install its Python dependencies with uv (installing uv first if missing)
  3. Register goldfish with Claude Code and/or the Claude desktop app, if found
Your notes stay on this computer. To undo everything later, run:
  bash ~/.local/share/goldfish/uninstall.sh
INFO
echo

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. A popup may appear asking to install Apple's developer tools —"
  echo "click Install, wait for it to finish, then run this command again."
  xcode-select --install >/dev/null 2>&1 || true
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — installing (https://astral.sh/uv)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "updating existing install at $INSTALL_DIR"
  if [ -n "$REF" ]; then
    git -C "$INSTALL_DIR" fetch --depth 1 origin "$REF" && git -C "$INSTALL_DIR" checkout -q FETCH_HEAD
  else
    git -C "$INSTALL_DIR" pull --ff-only
  fi
else
  echo "cloning to $INSTALL_DIR"
  if [ -n "$REF" ]; then
    git clone --depth 1 --branch "$REF" "$REPO_URL" "$INSTALL_DIR"
  else
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
fi

cd "$INSTALL_DIR"
echo "syncing dependencies..."
uv sync

UV_BIN="$(command -v uv)"
DESKTOP_DIR="$HOME/Library/Application Support/Claude"
found_client=0

if command -v claude >/dev/null 2>&1; then
  found_client=1
  echo "Claude Code found — enabling transcript capture (brain-mcp)..."
  uv run --directory packages/brain brain-mcp install cc || \
    echo "  (non-fatal — retry later with: cd $INSTALL_DIR && uv run --directory packages/brain brain-mcp install cc)"
  echo "registering goldfish with Claude Code (user scope)..."
  claude mcp remove goldfish -s user >/dev/null 2>&1 || true
  claude mcp add goldfish -s user -- "$UV_BIN" run --directory "$INSTALL_DIR" goldfish serve
fi

# Claude Desktop launches MCP servers without your shell PATH, hence the
# absolute uv path. Existing config is backed up and merged, never replaced.
if [ -d "/Applications/Claude.app" ] || [ -d "$HOME/Applications/Claude.app" ] || [ -d "$DESKTOP_DIR" ]; then
  found_client=1
  echo "Claude desktop app found — registering goldfish in its config..."
  mkdir -p "$DESKTOP_DIR"
  uv run python -m goldfish.desktop_config "$DESKTOP_DIR/claude_desktop_config.json" "$UV_BIN" "$INSTALL_DIR"
fi

if [ "$found_client" = 0 ]; then
  echo
  echo "Couldn't find Claude on this Mac. Install the Claude app from"
  echo "https://claude.ai/download, open it once, then run this command again."
  exit 1
fi

cat <<'EOF'

Done! Last step: fully quit Claude (Cmd+Q) and open it again.

Then check it works: start a new chat and ask
  "Run goldfish_status and tell me if each tier is healthy."
If Claude can't find the tool, quit Claude fully and reopen it once more.

Recommended for the Claude app: open Settings > Profile and paste this into
the personal preferences box, so Claude uses its memory in every chat:

  At the start of each chat, check goldfish_recall for what you know about me.
  Save important facts with goldfish_remember, and before we finish a real
  conversation, save a summary with goldfish_save_chat.
EOF
