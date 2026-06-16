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
  non-destructive write policy.
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

## Skills

The root `skills/` directory is generated from the dltHub AI workbench's `init`
toolkit, pinned to a commit. Don't hand-edit `skills/` — change the skills
upstream, then re-pull.

Knobs in `scripts/generate_skills.py`:
- `WORKBENCH_BRANCH` — the branch `update-skills` tracks.
- `WORKBENCH_REF_SHORT` — short commit SHA (the one GitHub shows); override by hand.
- `WORKBENCH_REF` — full SHA, written automatically from the short one; never hand-edit.
- `SKILL_TOOLKITS` — which toolkits' skills to include.

```bash
make update-skills                  # track WORKBENCH_BRANCH's latest commit
make update-skills REF=<branch|sha> # pin a specific branch tip or commit
make generate-skills                # rebuild at the pinned short SHA (auto-fills the full SHA)
make check-skills                   # CI drift guard
```

To pin a commit by hand, set `WORKBENCH_REF_SHORT` to a short SHA and run
`make generate-skills` — it resolves and writes the full `WORKBENCH_REF`.

One-off testing without touching the committed pins (env overrides):
`DLTHUB_WORKBENCH_REPO` (repo URL or local path), `DLTHUB_WORKBENCH_REF`
(branch/sha to build from), `DLTHUB_SKILL_TOOLKITS` (comma-separated toolkits).

## Code style

Write self-explanatory code. Do not add comments that narrate what the code
does; reserve comments for the non-obvious *why*.
