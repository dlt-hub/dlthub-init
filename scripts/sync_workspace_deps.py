"""Sync the bundled workspace scaffold's dependencies with dlt's `WORKSPACE_DEPS`.

dlt seeds the same dependency list into workspaces via its own `dlthub init`, and
keeps it in `dlt._workspace.cli.dlthub.utils.WORKSPACE_DEPS` under a comment saying
it is "kept in sync with the workspace deps that dlthub init seeds into the
scaffolded project". Nothing enforced that, and the copy in this repo sat frozen at
dlt's 2026-05-10 state while upstream moved on. This script makes upstream
authoritative: run `make scaffold-deps-sync` to pull the list, and
`make scaffold-deps-check` to fail on drift.

The reference dlt version is whatever the scaffold's own `uv.lock` resolves, so
bumping the lock is the only pin to maintain. `WORKSPACE_DEPS` is read out of the
published wheel rather than an installed dlt: `dlthub-init` deliberately does not
depend on dlt, since `uvx dlthub-init` runs before any dlt exists.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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

WORKSPACE_DEPS_MODULE = "dlt/_workspace/cli/dlthub/utils.py"
WORKSPACE_DEPS_NAME = "WORKSPACE_DEPS"
PYPI_URL = "https://pypi.org/pypi/dlt/{version}/json"
TIMEOUT = 30


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


def _wheel_url(version: str) -> str:
    url = PYPI_URL.format(version=version)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            payload = json.load(response)
    except OSError as exc:
        raise SyncError(f"cannot reach PyPI for dlt {version}: {exc}") from exc
    for entry in payload.get("urls", []):
        if entry.get("packagetype") == "bdist_wheel":
            return str(entry["url"])
    raise SyncError(f"dlt {version} has no wheel on PyPI")


def extract_workspace_deps(wheel_bytes: bytes) -> list[str]:
    """Parse WORKSPACE_DEPS out of a dlt wheel without importing dlt."""
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as wheel:
        try:
            source = wheel.read(WORKSPACE_DEPS_MODULE).decode("utf-8")
        except KeyError as exc:
            raise SyncError(f"{WORKSPACE_DEPS_MODULE} missing from the dlt wheel") from exc
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name) or node.target.id != WORKSPACE_DEPS_NAME:
                continue
            value_node = node.value
        elif isinstance(node, ast.Assign):
            targets = node.targets
            if len(targets) != 1 or not isinstance(targets[0], ast.Name) or targets[0].id != WORKSPACE_DEPS_NAME:
                continue
            value_node = node.value
        else:
            continue
        if value_node is None:
            continue
        try:
            value = ast.literal_eval(value_node)
        except ValueError as exc:
            raise SyncError(f"{WORKSPACE_DEPS_NAME} is not a literal list") from exc
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SyncError(f"{WORKSPACE_DEPS_NAME} is not a list of strings")
        return [str(item) for item in value]
    raise SyncError(f"{WORKSPACE_DEPS_NAME} not found in {WORKSPACE_DEPS_MODULE}")


def fetch_workspace_deps(version: str) -> list[str]:
    url = _wheel_url(version)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            wheel_bytes: bytes = response.read()
    except OSError as exc:
        raise SyncError(f"cannot download {url}: {exc}") from exc
    return extract_workspace_deps(wheel_bytes)


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
            f"upstream WORKSPACE_DEPS now carries {', '.join(overlap)}; "
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
            print(f"scaffold deps: OK — in sync with dlt {version} WORKSPACE_DEPS.")
            return 0
        if args.check:
            print(f"scaffold deps: FAILED — drift against dlt {version} WORKSPACE_DEPS:")
            _report_drift(current, desired)
            print("Run 'make scaffold-deps-sync' (then 'make scaffold-lock-upgrade') and commit.")
            return 1
        write_dependencies(desired)
        print(f"scaffold deps: synced with dlt {version} WORKSPACE_DEPS:")
        _report_drift(current, desired)
        print("Run 'make scaffold-lock-upgrade' to re-resolve the bundled uv.lock, then commit.")
    except SyncError as exc:
        print(f"sync_workspace_deps: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
