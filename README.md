# dlthub-init (beta)

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
| `--no-telemetry` | Disable usage telemetry for this run. |
| `--verbose`, `-v` | Stream output from `uv`. |

## Collision behavior

`dlthub-init` is safe to run in an existing directory:

- Missing files are **created**.
- The run stops only if `.dlt/.workspace` already exists — the directory is
  already a dltHub workspace (override with `--force`).
- Otherwise existing files are **left alone** and reported as skipped: your
  `pyproject.toml`, `.dlt/config.toml`, and `.dlt/secrets.toml` are never
  overwritten, and `.gitignore` is skipped (or **merged** with `--merge`).
- `uv.lock` is written only when `pyproject.toml` is created, so the lockfile
  always matches the workspace's dependencies.
- `--force` overwrites the generated files (never secrets).

## Telemetry

`dlthub-init` sends anonymous usage events so we can improve the scaffolding
experience.

No personal data is collected, and no workspace contents are ever sent.

Telemetry is controlled by the following, in order of precedence:

1. the `--no-telemetry` flag,
2. `DLTHUB_INIT_TELEMETRY=0` (or `false`/`off`),
3. `DO_NOT_TRACK=1`,
4. an existing dlt opt-out (`~/.dlt/config.toml` `[runtime] dlthub_telemetry = false`,
   or `RUNTIME__DLTHUB_TELEMETRY=false`).

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
