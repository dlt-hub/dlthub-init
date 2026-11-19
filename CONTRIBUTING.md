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

- `src/dlthub_init/` — the CLI. `cli.py` parses the options and runs the steps;
  `dlthub.py` builds the `dlthub` commands for the installed dlt version and runs
  them attached to the terminal; `uv.py` runs `uv sync`.
- `tests/` — fast unit tests. `tests_integration/` — slow end-to-end tests that
  run the real `dlthub init` of the installed dlt, fetch the AI harness and run
  `uv sync`.

dlthub-init bundles no workspace files and no skills. Everything it creates
comes from `dlthub init` and `dlthub ai init`, so a change to the workspace or to
the agent setup belongs in dlt or in the AI harness, not here.

## Testing another dlt

The dev environment is locked to a dlt pre-release that merges into existing
projects, set by `constraint-dependencies` in `pyproject.toml`. Drop the
constraint once dlt 1.33.0 is released. CI also runs the integration tests on
older dlt, which runs `dlthub init` and then `dlthub ai init`. To do the same
locally:

```bash
uv run --with "dlt==1.32.0" pytest tests_integration
```

To run against a local dlt checkout, install it into a separate environment:

```bash
uv venv /tmp/dlthub-init-venv
uv pip install --python /tmp/dlthub-init-venv/bin/python -e . /path/to/dlt
/tmp/dlthub-init-venv/bin/dlthub-init /tmp/ws --agent claude --no-sync
```

A dlt installed from a path or git is reproduced in the workspace's
`[tool.uv.sources]`, so `uv sync` there installs the same dlt.

## Telemetry

The CLI sends one anonymous usage event per run to PostHog's capture API, with a
plain HTTP request. Users opt out with `--no-telemetry`, `DLTHUB_INIT_TELEMETRY=0`,
or `DO_NOT_TRACK=1`. A dlt opt-out (`runtime.dlthub_telemetry = false`) is resolved
by dlt from its usual config and environment, and is honored. The first three also
set `RUNTIME__DLTHUB_TELEMETRY=false` for the `dlthub` commands the CLI runs. The
device id is dlt's anonymous id.

Each event carries the dlt version and, on a failed `dlthub` command, the step
that failed (`init` or `ai init`).

For development and testing, three environment variables override the defaults:

| Variable | Effect |
|---|---|
| `DLTHUB_INIT_TELEMETRY` | Force telemetry on (`1`/`true`/`yes`/`on`) or off (any other value). |
| `DLTHUB_INIT_POSTHOG_KEY` | Override the bundled PostHog project key. |
| `DLTHUB_INIT_POSTHOG_HOST` | Override the PostHog host (default `https://eu.i.posthog.com`). |

Released builds bake the project key into a gitignored `_telemetry_key.py`; a dev
checkout has no key, so telemetry stays disabled until you set
`DLTHUB_INIT_POSTHOG_KEY`. To exercise the full path against a throwaway PostHog
project:

```bash
DLTHUB_INIT_TELEMETRY=1 \
DLTHUB_INIT_POSTHOG_KEY=phc_your_test_key \
DLTHUB_INIT_POSTHOG_HOST=https://eu.i.posthog.com \
  uv run dlthub-init my-workspace --agent claude
```

For releases, put the real key in a gitignored `.make.env`
(`DLTHUB_INIT_POSTHOG_KEY=phc_…`); the Makefile loads it into `uv build`, and
`make publish` refuses to run without it.

## Code style

Write self-explanatory code. Do not add comments that narrate what the code
does; reserve comments for the non-obvious *why*.
