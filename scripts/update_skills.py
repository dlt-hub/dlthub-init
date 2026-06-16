"""Bump the pinned workbench commit and regenerate skills/.

Run via `make update-skills [REF=<branch-or-sha>]`. With no argument, tracks the
WORKBENCH_BRANCH tip. Writes WORKBENCH_REF_SHORT, then runs generate_skills.py,
which resolves it to the full SHA (WORKBENCH_REF) and rebuilds skills/.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GENERATE_SCRIPT = SCRIPT_DIR / "generate_skills.py"

sys.path.insert(0, str(SCRIPT_DIR))

from generate_skills import WORKBENCH_BRANCH, WORKBENCH_REF_SHORT, WORKBENCH_REPO  # noqa: E402

_SHORT_RE = re.compile(r'^(?P<prefix>WORKBENCH_REF_SHORT\s*=\s*)"[^"]*"', re.MULTILINE)
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_SHORT_LEN = 7


def _resolve_short(arg: str | None) -> str:
    ref = (arg or WORKBENCH_BRANCH).strip()
    if _SHA_RE.match(ref):
        return ref[:_SHORT_LEN]
    print(f"Resolving branch {ref!r} on {WORKBENCH_REPO} ...")
    out = subprocess.run(
        ["git", "ls-remote", WORKBENCH_REPO, f"refs/heads/{ref}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not out:
        print(f"error: branch {ref!r} not found on {WORKBENCH_REPO}", file=sys.stderr)
        raise SystemExit(1)
    return out.split()[0][:_SHORT_LEN]


def _write_short(short: str) -> None:
    content = GENERATE_SCRIPT.read_text(encoding="utf-8")
    new_content, count = _SHORT_RE.subn(rf'\g<prefix>"{short}"', content)
    if count != 1:
        print(f"error: expected one WORKBENCH_REF_SHORT assignment, found {count}", file=sys.stderr)
        raise SystemExit(1)
    GENERATE_SCRIPT.write_text(new_content, encoding="utf-8")


def main(argv: list[str]) -> int:
    short = _resolve_short(argv[0] if argv else None)
    if short == WORKBENCH_REF_SHORT:
        print(f"WORKBENCH_REF_SHORT already {short}; regenerating anyway.")
    else:
        print(f"Bumping WORKBENCH_REF_SHORT: {WORKBENCH_REF_SHORT} -> {short}")
        _write_short(short)
    subprocess.run([sys.executable, str(GENERATE_SCRIPT)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
