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
`uv.lock` pins exact versions for reproducible installs.

Its dependency list is generated from dlt's `WORKSPACE_DEPS`, the same list dlt
seeds from its own `dlthub init`. Don't hand-edit it: change `WORKSPACE_DEPS`
upstream, then re-sync, or CI fails and the next sync reverts the edit.

Knobs in `scripts/sync_workspace_deps.py`:
- `BASE_SPECS` — specs this repo owns (`dlt[hub]`, `dlthub`, `dlthub-client`),
  emitted ahead of the synced entries and never overwritten by a sync.
- `WORKSPACE_DEPS_MODULE` / `WORKSPACE_DEPS_NAME` — where the list lives in the
  dlt wheel; both fail loud if upstream moves or renames it.

The reference dlt version is whatever the scaffold's `uv.lock` resolves, so the
lock is the only pin to maintain.

```bash
make scaffold-deps-sync     # pull WORKSPACE_DEPS from the locked dlt version
make scaffold-deps-check    # CI drift guard
make scaffold-lock-upgrade  # refresh the lock after a sync, then commit
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

## Telemetry

The CLI sends anonymous usage events to PostHog. Users opt out with `--no-telemetry`,
`DLTHUB_INIT_TELEMETRY=0`, or `DO_NOT_TRACK=1`, and an existing dlt opt-out
(`runtime.dlthub_telemetry = false` in dlt's global `config.toml`, or
`RUNTIME__DLTHUB_TELEMETRY=0`) is honored.

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
  uv run dlthub-init my-workspace --yes
```

For releases, put the real key in a gitignored `.make.env`
(`DLTHUB_INIT_POSTHOG_KEY=phc_…`); the Makefile loads it into `uv build`, and
`make publish` refuses to run without it.

## Testing against a local platform stack

`make workspace-local` scaffolds `./$(WORKSPACE_DIR)` with `api.dlthub.test` and
`auth.dlthub.test` pinned into its `.dlt/config.toml`. `dlthub-init` never talks
to a stack itself, so everything below happens afterwards, against the workspace
that target produces. Workspaces under `examples/` are gitignored and disposable.

`make workspace-dev` pins `api.dlthub.dev` instead. The connect, deploy and
scheduling steps below apply there too, but the TLS and login workarounds are
local-only: the dev stack serves real certificates and shares the auth host with
the API, which is why the target sets neither `DLT_RUNTIME_INSECURE` nor
`AUTH_BASE_URL`. It has not been exercised here.

The local stack serves mkcert certificates that Python does not trust, so every
remote `dlthub` command fails with `CERTIFICATE_VERIFY_FAILED` until one of
these is set:

| Variable | Effect |
|---|---|
| `DLT_RUNTIME_INSECURE` | Skip TLS verification (`1`/`true`/`yes`). This is what `make workspace-local` prints. Covers auth, API, dataplane, uploads and log streaming; every other client stays verified by default. |
| `SSL_CERT_FILE` | Trust the local CA instead: `$(mkcert -CAROOT)/rootCA.pem`. Keeps verification on. |

Log in with the device flow. The default browser loopback flow fails against the
local mock identity service with `invalid_grant`.

```bash
uv run dlthub login --device          # prints a verification URL and a resume code
uv run dlthub login --resume <code>   # after approving in the browser
```

Then connect and deploy. Non-interactive runs need explicit ids, and `connect`
rebinds the directory, writing `workspace_id` and `organization_id` under
`[runtime]` plus the name under `[workspace.settings]`.

```bash
uv run dlthub workspace list
uv run dlthub workspace connect --create <name> --org-id <org-uuid>
uv run dlthub deploy --dry-run        # preview; --show-manifest dumps the YAML
uv run dlthub deploy
```

Jobs come from `__deployment__.py`. Schedule them with cron triggers:

```python
from dlt.hub import run
from dlt.hub.run import trigger

@run.pipeline("hourly_metrics", trigger=trigger.schedule("0 * * * *"))
def load_hourly_metrics():
    ...
```

Two things that cost time:

- `deploy` registers jobs and their schedules but never runs them. Force a run
  with `uv run dlthub run <job>`.
- `destination="warehouse"`, which the bundled skills recommend, is not defined
  in the scaffold. Use `destination="duckdb"`, or add the named destination to
  `.dlt/config.toml`.

## Code style

Write self-explanatory code. Do not add comments that narrate what the code
does; reserve comments for the non-obvious *why*.
