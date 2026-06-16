# dlthub-init

Scaffold a [dltHub](https://dlthub.com) workspace into a new or existing directory.

`dlthub-init` lays down the files of a minimal dltHub workspace — `pyproject.toml`,
a locked `uv.lock`, and the `.dlt/` configuration — and optionally creates the
virtual environment. That is all it does: it does not log in, run a pipeline, or
install agent toolkits.

Unlike `dlthub-start`, it is safe to run inside an existing repository. It is
non-destructive by default: it never overwrites your files, and it stops before
writing anything if a generated path would collide with something already there.

## Usage

```bash
uvx dlthub-init             # initialize the current directory
uvx dlthub-init my-workspace  # initialize ./my-workspace
```

After scaffolding, `dlthub-init` offers to create a virtual environment and
install dependencies with `uv`.

### Options

| Flag | Effect |
| --- | --- |
| `--no-sync` | Scaffold files only; do not create a venv or install dependencies. |
| `--force` | Overwrite existing generated files (never secrets). |
| `--merge` | Append missing entries to an existing `.gitignore` instead of skipping it. |
| `--no-pyproject` | Skip `pyproject.toml`. |
| `--no-gitignore` | Skip `.gitignore`. |
| `--verbose`, `-v` | Stream output from `uv`. |

## Collision behavior

`dlthub-init` is safe to run in an existing directory:

- Missing files are **created**.
- An existing `.gitignore` is **skipped** (or **merged** with `--merge`).
- An existing secrets file (`.dlt/secrets.toml`) is **never** touched.
- Any other existing generated file is a **hard collision**: the run stops
  before writing anything (override with `--force`).

## Development

```bash
make dev      # install dev dependencies
make lint     # ruff + mypy
make test     # unit tests
make ci       # full local CI
```

The bundled workspace lives in `src/dlthub_init/scaffolds/minimal_workspace`.
After editing its `pyproject.toml`, run `make scaffold-lock-upgrade` to refresh
the committed `uv.lock`.
