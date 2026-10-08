"""Register goldfish in Claude Desktop's claude_desktop_config.json.

Usage: python -m goldfish.desktop_config <config_path> <uv_bin> <install_dir>

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


if __name__ == "__main__":
    register(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
