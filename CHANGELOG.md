# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-07-07

### Changed
- Refreshed the bundled skills to workbench `e8bcc26`: the `dlthub-router` skill now only runs the `dlthub ai status` verification when the install result is ambiguous or MCP hasn't been checked this session, instead of every time.
- Refreshed the bundled minimal workspace `uv.lock` to the latest within-constraint dependency versions (notably `dlthub-client` `0.28.0` → `0.28.1`; plus transitive bumps to `fastmcp`, `marimo`, `narwhals`, `uvicorn`, `typing-extensions`, and others).

## [0.2.1] - 2026-07-01

### Added
- Scaffold a committed `.python-version` (pinned to `3.13`) into the minimal workspace so a new workspace gets a self-contained, reproducible venv — uv auto-provisions the interpreter on `uv sync`. Removed the matching `.gitignore` entry so the pin is tracked; existing `.python-version` files are left untouched.

## [0.2.0] - 2026-06-30

### Added
- Anonymous usage telemetry: `dlthub-init` now emits a telemetry event on a command execution. Opt out with `--no-telemetry`, `DLTHUB_INIT_TELEMETRY=0`, `DO_NOT_TRACK=1`, or an existing dlt opt-out. See the README "Telemetry" section.
- Scaffold a `__deployment__.py` deployment manifest into the minimal workspace — an empty stub (with guidance) where you import the pipelines and notebooks to deploy and list them in `__all__`.

### Changed
- Refreshed the root and bundled minimal workspace `uv.lock` files to the latest within-constraint dependency versions (notably `dlthub-client` `0.27.9` → `0.28.0`; dev tooling `pytest` `9.1.0` → `9.1.1` and `ruff` `0.15.17` → `0.15.20`).

## [0.1.2] - 2026-06-23

### Changed
- Refreshed the bundled skills and the minimal workspace `uv.lock`.

## [0.1.1] - 2026-06-18

### Changed
- Refreshed the bundled minimal workspace `uv.lock`, bumping `dlt` to `1.28.0` along with its transitive dependencies.

## [0.1.0] - 2026-06-16

### Added
- Initial release: `uvx dlthub-init [dir]` scaffolds a dltHub workspace into a new or existing directory and optionally creates the virtual environment.
- Non-destructive by default: safe to run in an existing directory. The run stops only if `.dlt/.workspace` already exists (the directory is already a workspace, exit code `2`); any other existing file is left untouched and reported as skipped. `uv.lock` is written only alongside a freshly created `pyproject.toml`. Flags: `--force`, `--merge`, `--no-pyproject`, `--no-gitignore`, `--no-sync`, `--yes`.
- Bundled minimal workspace with loosened dependency ranges and a committed `uv.lock` for reproducible installs.
- `uv sync` runs by default behind an interactive confirmation; a failed sync degrades to a warning so the scaffold still succeeds.
- `make generate-skills` / `update-skills` / `check-skills` populate the root `skills/` directory from the dltHub AI workbench's `init` toolkit, pinned to a `WORKBENCH_REF` commit (with a CI drift guard), mirroring `dlthub-start`'s AI-generation flow.
- Scaffolded workspaces receive the bundled skills: copied into `.agents/skills/` (the canonical location most agents read) and linked into `.claude/skills/` via relative symlinks (copied on Windows or when symlinks are unavailable). The skills ship in the wheel from the single-source `skills/` directory.
- After scaffolding, the next steps point you to open your coding agent in the workspace (the `cd` and `uv sync` steps drop out when not needed).
