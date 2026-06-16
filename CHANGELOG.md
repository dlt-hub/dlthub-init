# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release: `uvx dlthub-init [dir]` scaffolds a dltHub workspace into a new or existing directory and optionally creates the virtual environment. No login, pipeline run, or agent toolkits.
- Non-destructive by default: a preflight aborts before writing anything if a generated file would collide (exit code `2`). An existing `.gitignore` is skipped (`--merge` to append), and `.dlt/secrets.toml` is never overwritten. Flags: `--force`, `--merge`, `--no-pyproject`, `--no-gitignore`, `--no-sync`, `--yes`.
- Bundled minimal workspace with loosened dependency ranges and a committed `uv.lock` for reproducible installs.
- `uv sync` runs by default behind an interactive confirmation; a failed sync degrades to a warning so the scaffold still succeeds.
