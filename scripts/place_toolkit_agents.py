"""Place a toolkit's background agents into a workspace.

Workaround. `dlthub ai toolkit install` installs a toolkit's skills, rules and
commands but never its agents: dlt looks for them at `<toolkit>/agents/`
(`dlt/_workspace/cli/dlthub/ai/commands.py`) while the workbench ships them at
`<toolkit>/dlthub/agents/`. The directory it checks does not exist, the block is
skipped, and nothing is logged — so the install reports success and a later
`agent("<toolkit>:<name>")` fails with "toolkit is not installed".

Copies from the workbench clone the installer already made, into the same place
the installer would have. Delete this script and its Makefile call once dlt
resolves the source path.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

WORKBENCH_CLONE = Path.home() / ".dlt" / "repos" / "dlthub-ai-workbench" / "workbench"
AGENTS_SUBDIR = Path("dlthub") / "agents"
DESTINATION = Path(".claude") / "dlthub" / "agents"


def place(workspace: Path, toolkit: str) -> list[str]:
    """Copy one toolkit's agent folders into the workspace. Returns the names placed."""
    source = WORKBENCH_CLONE / toolkit / AGENTS_SUBDIR
    if not source.is_dir():
        return []

    target = workspace / DESTINATION
    target.mkdir(parents=True, exist_ok=True)
    placed: list[str] = []
    for agent_dir in sorted(source.iterdir()):
        if not agent_dir.is_dir() or not (agent_dir / "AGENT.md").is_file():
            continue
        shutil.copytree(agent_dir, target / agent_dir.name, dirs_exist_ok=True)
        placed.append(agent_dir.name)
    return placed


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: place_toolkit_agents.py <workspace-dir> <toolkit> [toolkit ...]", file=sys.stderr)
        return 2

    workspace = Path(argv[1])
    if not workspace.is_dir():
        print(f"place_toolkit_agents: {workspace} not found", file=sys.stderr)
        return 1
    if not WORKBENCH_CLONE.is_dir():
        print(
            f"place_toolkit_agents: no workbench clone at {WORKBENCH_CLONE}."
            " Run 'dlthub ai toolkit install <toolkit>' first.",
            file=sys.stderr,
        )
        return 1

    total: list[str] = []
    for toolkit in argv[2:]:
        placed = place(workspace, toolkit)
        if not placed:
            print(f"place_toolkit_agents: no agents found for toolkit {toolkit!r}")
        total.extend(f"{toolkit}:{name}" for name in placed)

    if total:
        print(f"place_toolkit_agents: placed {', '.join(total)} in {workspace / DESTINATION}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
