#!/usr/bin/env bash
# Goldfish one-command installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lucasjamesss/goldfish/master/install.sh | bash
#
# Idempotent — safe to re-run. Clones/updates goldfish, syncs its Python env,
# enables brain-mcp's transcript-capture hooks for Claude Code, and registers
# the goldfish MCP server with the `claude` CLI if it's on PATH.

set -euo pipefail

REPO_URL="https://github.com/lucasjamesss/goldfish.git"
INSTALL_DIR="${GOLDFISH_HOME:-$HOME/.local/share/goldfish}"

echo "== Goldfish installer =="

if ! command -v git >/dev/null 2>&1; then
  echo "git is required — install it and re-run." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found — installing (https://astral.sh/uv)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "cloning to $INSTALL_DIR"
  git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
echo "syncing dependencies..."
uv sync

echo "enabling transcript capture for Claude Code (brain-mcp)..."
uv run --directory packages/brain brain-mcp install cc || \
  echo "  (non-fatal — retry later with: cd $INSTALL_DIR && uv run --directory packages/brain brain-mcp install cc)"

if command -v claude >/dev/null 2>&1; then
  echo "registering goldfish as an MCP server (user scope)..."
  claude mcp remove goldfish -s user >/dev/null 2>&1 || true
  claude mcp add goldfish -s user -- uv run --directory "$INSTALL_DIR" goldfish serve
else
  cat <<EOF
claude CLI not found on PATH — add this to your MCP config manually:
  "goldfish": {
    "command": "uv",
    "args": ["run", "--directory", "$INSTALL_DIR", "goldfish", "serve"]
  }
EOF
fi

cat <<EOF

Done. Restart Claude Code (or run /mcp) to pick up the new tools:
  goldfish_search, goldfish_context, goldfish_remember, goldfish_recall, goldfish_status

The claude-mem tier (goldfish_context) reads a database that claude-mem's own
plugin populates — that's a separate install, not run by this script. See
packages/claude-mem/README.md if you want it too. Everything else works now.
EOF
