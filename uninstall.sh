#!/usr/bin/env bash
# Goldfish uninstaller. Safe to re-run.
#
#   bash ~/.local/share/goldfish/uninstall.sh            # unregister + remove install
#   bash ~/.local/share/goldfish/uninstall.sh --keep-code # unregister only
#
# Removes: the Claude Code registration, the Claude desktop app entry, the
# transcript-capture hooks and scheduler, and the install folder.
# NEVER removes your notes or transcript history. Those stay where they are:
#   ~/.goldfish/memory   (curated notes, PERSONA.md)
#   brain-mcp's data folder (printed below) -- delete it yourself if you want it gone.
set -uo pipefail

INSTALL_DIR="${GOLDFISH_HOME:-$HOME/.local/share/goldfish}"
DESKTOP_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
KEEP_CODE=0
[ "${1:-}" = "--keep-code" ] && KEEP_CODE=1

echo "== Goldfish uninstaller =="

if command -v claude >/dev/null 2>&1; then
  claude mcp remove goldfish -s user >/dev/null 2>&1 \
    && echo "  removed from Claude Code" || echo "  not registered in Claude Code"
fi

if [ -d "$INSTALL_DIR" ] && command -v uv >/dev/null 2>&1; then
  uv run --directory "$INSTALL_DIR/packages/brain" brain-mcp uninstall 2>&1 | sed 's/^/  /' || true
  [ -f "$DESKTOP_CFG" ] && uv run --directory "$INSTALL_DIR" python -m goldfish.desktop_config --remove "$DESKTOP_CFG"
else
  echo "  could not find $INSTALL_DIR or uv, so hooks and the desktop entry were not touched."
  echo "  Remove the \"goldfish\" entry from $DESKTOP_CFG by hand if it is there."
fi

if [ "$KEEP_CODE" = 0 ] && [ -d "$INSTALL_DIR" ]; then
  rm -rf "$INSTALL_DIR" && echo "  removed $INSTALL_DIR"
fi

echo
echo "Done. Your notes and history are untouched:"
echo "  ~/.goldfish/memory"
echo "Fully quit Claude (Cmd+Q) and reopen it so the tools disappear."
