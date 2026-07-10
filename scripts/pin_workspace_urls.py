"""Pin runtime base URLs into a scaffolded workspace's .dlt/config.toml.

This is a *manual test convenience* used by the `workspace-env` / `workspace-local`
Makefile targets. `dlthub-init` itself never talks to a stack at scaffold time and
has no --api-base-url/--auth-base-url flags; but a developer who wants to exercise a
later `dlthub workspace connect` against a local/dev/stage stack needs api_base_url /
auth_base_url pinned under [runtime] (that is where `connect` reads them from).

Idempotent: replaces existing keys in-place and inserts missing ones directly under
the [runtime] header (creating the section if absent).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _upsert(text: str, key: str, value: str) -> str:
    line = f'{key}="{value}"'
    # Replace an existing top-level `key=...` assignment if present.
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    # Otherwise insert directly after the [runtime] header.
    if "[runtime]" in text:
        return text.replace("[runtime]\n", f"[runtime]\n{line}\n", 1)
    # No [runtime] section at all — append one.
    sep = "" if text.endswith("\n") or not text else "\n"
    return f"{text}{sep}\n[runtime]\n{line}\n"


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: pin_workspace_urls.py <config.toml> <api_base_url> <auth_base_url>",
            file=sys.stderr,
        )
        return 2

    config_path, api_base_url, auth_base_url = Path(argv[1]), argv[2], argv[3]
    if not config_path.is_file():
        print(f"pin_workspace_urls: {config_path} not found", file=sys.stderr)
        return 1

    text = config_path.read_text(encoding="utf-8")
    text = _upsert(text, "api_base_url", api_base_url)
    text = _upsert(text, "auth_base_url", auth_base_url)
    config_path.write_text(text, encoding="utf-8")

    print(f"pin_workspace_urls: pinned api_base_url/auth_base_url into {config_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
