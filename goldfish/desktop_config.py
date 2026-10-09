"""Register goldfish in Claude Desktop's claude_desktop_config.json.

Usage: python -m goldfish.desktop_config <config_path> <uv_bin> <install_dir>
       python -m goldfish.desktop_config --remove <config_path>

Merges into the existing file (backed up to .json.bak first) so other MCP
servers and settings are kept.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def register(cfg: Path, uv_bin: str, install_dir: str) -> None:
    data: dict = {}
    if cfg.exists() and cfg.read_text().strip():
        shutil.copy(cfg, cfg.with_suffix(".json.bak"))
        data = json.loads(cfg.read_text())
    data.setdefault("mcpServers", {})["goldfish"] = {
        "command": uv_bin,
        "args": ["run", "--directory", install_dir, "goldfish", "serve"],
    }
    cfg.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  wrote {cfg}")


def unregister(cfg: Path) -> None:
    """Remove only the goldfish entry; every other setting stays untouched."""
    if not cfg.exists() or not cfg.read_text().strip():
        print("  nothing to remove (no desktop config)")
        return
    data = json.loads(cfg.read_text())
    servers = data.get("mcpServers", {})
    if "goldfish" not in servers:
        print("  goldfish was not registered in the desktop app")
        return
    shutil.copy(cfg, cfg.with_suffix(".json.bak"))
    del servers["goldfish"]
    cfg.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  removed goldfish from {cfg} (backup: .json.bak)")


if __name__ == "__main__":
    if sys.argv[1] == "--remove":
        unregister(Path(sys.argv[2]))
    else:
        register(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
