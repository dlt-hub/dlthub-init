# Contributing to dlthub-init

## Setup

```bash
make dev
```

## Checks

```bash
make fl       # format + lint-fix
make lint     # ruff + mypy (no writes)
make test     # unit tests
make ci       # everything CI runs
```

## Layout

- `src/dlthub_init/` — the CLI. `cli.py` orchestrates the flow; `scaffold.py`
  enumerates and writes the payload; `collisions.py` implements the
  non-destructive write policy (see `COLLISION_PLAN.md`).
- `src/dlthub_init/scaffolds/minimal_workspace/` — the bundled workspace copied
  into the user's directory.
- `tests/` — fast unit tests. `tests_integration/` — slow end-to-end tests that
  invoke the real CLI and `uv sync`.

## The bundled workspace

The scaffold's `pyproject.toml` uses loose dependency ranges; the committed
`uv.lock` pins exact versions for reproducible installs. After changing the
scaffold's dependencies, refresh the lock and commit it:

```bash
make scaffold-lock-upgrade
```

## Code style

Write self-explanatory code. Do not add comments that narrate what the code
does; reserve comments for the non-obvious *why*.
