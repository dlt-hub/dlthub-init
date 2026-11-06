"""Sync the bundled workspace scaffold's dependencies with dlt's `workspace_deps()`."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD_DIR = REPO_ROOT / "src" / "dlthub_init" / "scaffolds" / "minimal_workspace"
SCAFFOLD_PYPROJECT = SCAFFOLD_DIR / "pyproject.toml"
SCAFFOLD_LOCK = SCAFFOLD_DIR / "uv.lock"

BASE_SPECS: tuple[str, ...] = (
    "dlt[hub]>=1.27.2,<2",
    "dlthub>=0.27.0,<1",
    "dlthub-client>=0.27.7,<1",
)

# Specs contain brackets (`dlt[hub]`), so the array ends at the first `]` on its own line.
_DEPENDENCIES_RE = re.compile(r"^dependencies = \[$.*?^\]$", re.MULTILINE | re.DOTALL)
_LEADING_NAME_RE = re.compile(r"^\s*([A-Za-z0-9._-]+)")
_NORMALIZE_RE = re.compile(r"[-_.]+")

PROBE_SCRIPT = REPO_ROOT / "scripts" / "probe_workspace_deps.py"
TIMEOUT = 300


class SyncError(Exception):
    """Raised when the upstream list cannot be resolved or the scaffold cannot be rewritten."""


def scaffold_dlt_version(lock_path: Path = SCAFFOLD_LOCK) -> str:
    """Return the dlt version the scaffold's uv.lock resolves."""
    try:
        lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SyncError(f"cannot read {lock_path}: {exc}") from exc
    for package in lock.get("package", []):
        if package.get("name") == "dlt":
            version = package.get("version")
            if not isinstance(version, str):
                raise SyncError(f"dlt entry in {lock_path} has no version")
            return version
    raise SyncError(f"no dlt package found in {lock_path}")


def probe_command(version: str, uv: str = "uv") -> list[str]:
    return [
        uv,
        "run",
        "--isolated",
        "--no-project",
        "--with",
        f"dlt=={version}",
        "python",
        "-I",
        str(PROBE_SCRIPT),
    ]


def parse_workspace_deps(stdout: str) -> list[str]:
    # last non-empty line: dlt may log to stdout first
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise SyncError("probe printed nothing")
    try:
        value = json.loads(lines[-1])
    except ValueError as exc:
        raise SyncError(f"probe did not print JSON: {lines[-1]!r}") from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SyncError("workspace_deps() did not return a list of strings")
    return [str(item) for item in value]


def fetch_workspace_deps(version: str) -> list[str]:
    uv = shutil.which("uv")
    if uv is None:
        raise SyncError("uv is not on PATH")
    command = probe_command(version, uv)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"cannot run the dlt {version} probe: {exc}") from exc
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-15:])
        raise SyncError(f"dlt {version} probe failed (exit {result.returncode}):\n{tail}")
    return parse_workspace_deps(result.stdout)


def package_name(spec: str) -> str:
    """PEP 503 normalized distribution name for a PEP 508 spec."""
    match = _LEADING_NAME_RE.match(spec)
    if match is None:
        raise SyncError(f"cannot read a package name from spec {spec!r}")
    return _NORMALIZE_RE.sub("-", match.group(1)).lower()


def merge_specs(base: tuple[str, ...], upstream: list[str]) -> list[str]:
    """Concatenate BASE_SPECS with upstream's list, refusing to emit a package twice."""
    overlap = sorted({package_name(spec) for spec in base} & {package_name(spec) for spec in upstream})
    if overlap:
        raise SyncError(
            f"upstream workspace_deps() now carries {', '.join(overlap)}; "
            "drop it from BASE_SPECS so the scaffold does not pin it twice"
        )
    return list(base) + upstream


def render_dependencies(specs: list[str]) -> str:
    body = "".join(f'    "{spec}",\n' for spec in specs)
    return f"dependencies = [\n{body}]"


def read_dependencies(pyproject_path: Path = SCAFFOLD_PYPROJECT) -> list[str]:
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SyncError(f"cannot read {pyproject_path}: {exc}") from exc
    deps = data.get("project", {}).get("dependencies", [])
    return [str(item) for item in deps]


def write_dependencies(specs: list[str], pyproject_path: Path = SCAFFOLD_PYPROJECT) -> None:
    text = pyproject_path.read_text(encoding="utf-8")
    match = _DEPENDENCIES_RE.search(text)
    if match is None:
        raise SyncError(f"no dependencies array in {pyproject_path}")
    pyproject_path.write_text(
        text[: match.start()] + render_dependencies(specs) + text[match.end() :], encoding="utf-8"
    )


def _report_drift(current: list[str], desired: list[str]) -> None:
    missing = [spec for spec in desired if spec not in current]
    extra = [spec for spec in current if spec not in desired]
    for spec in missing:
        print(f"    + {spec}")
    for spec in extra:
        print(f"    - {spec}")
    if not missing and not extra:
        print("    (same entries, different order)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Report drift and exit non-zero instead of rewriting.")
    args = parser.parse_args(argv)

    try:
        version = scaffold_dlt_version()
        desired = merge_specs(BASE_SPECS, fetch_workspace_deps(version))
        current = read_dependencies()
        if current == desired:
            print(f"scaffold deps: OK — in sync with dlt {version} workspace_deps().")
            return 0
        if args.check:
            print(f"scaffold deps: FAILED — drift against dlt {version} workspace_deps():")
            _report_drift(current, desired)
            print("Run 'make scaffold-deps-sync' (then 'make scaffold-lock-upgrade') and commit.")
            return 1
        write_dependencies(desired)
        print(f"scaffold deps: synced with dlt {version} workspace_deps():")
        _report_drift(current, desired)
        print("Run 'make scaffold-lock-upgrade' to re-resolve the bundled uv.lock, then commit.")
    except SyncError as exc:
        print(f"sync_workspace_deps: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
