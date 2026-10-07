# Agent jobs workspace

Dev-only workspace for the background agents hackathon: five pipelines that fail
in four different ways, and the scaffolding to write agents that diagnose them.

`make workspace-agent` from the repo root builds it into `examples/agent-workspace`
and prints the commands to deploy it. It lives outside `src/` because it pins
prerelease versions of `dlt` and `dlthub-client` that must not ship in the wheel.

## The pipelines

`jaffle_shop/` runs against the live [Jaffle Shop API](https://jaffle-shop.dlthub.com/docs).
Fire them all with `dlthub job trigger tag:jaffle`.

| pipeline | outcome | the bug |
|---|---|---|
| `correct` | 935 / 10 / 6 rows | the reference |
| `bad_config` | **fails** | `base_url` on `/api/v2/`, 404 on the first request |
| `bad_incremental` | **fails** | `cursor_path` on a field the API does not have |
| `bad_pagination` | **green**, 100 of 935 rows | paginator reads `next` from the body; this API uses the `Link` header |
| `bad_selector` | **green**, 0 of 6 rows | `data_selector` points at `data.results`; the API returns a bare array |

Two fail outright. **The other two lose data without failing** — they finish
green, so no job-status trigger sees them at all.

## The two steps

**1. Set up the verified agent.** `verified_agent.py` is a stub with the three
lines you need: declare `dlthub-platform:job-inspector` and give it a trigger.
Add it to `__deployment__.py`, deploy, and run `dlthub job trigger tag:jaffle`.
Each team watches a different pipeline, so we see different failures. Then read
what it says: is the diagnosis right, and useful to someone who has to act on it?

**2. Write your own.** `my_agent.py` is a stub; `example_agent.py` is a working
agent to copy. Pick something the workspace cannot do yet — `alerts.py` records
that a job failed but never why, and nothing wakes for the two green pipelines.

A fresh deploy has no agents. Both steps end the same way: write a file, add it
to `__deployment__.py`, deploy.

## The other jobs

| job | needs a key | needs the platform | answers |
|---|---|---|---|
| `loop_probe` | yes | no | can the loop authenticate at all |
| `endpoint_report` | no | no | which endpoint resolved, and whether `AGENT__*` arrived |

## Model keys

A run needs a key in two places: `export AGENT__API_KEY=<key>` for local runs, and
a workspace variable for deployed ones, because the runner cannot see your shell.

```bash
uv run dlthub variable set AGENT__API_KEY --value <key> --secret --workspace
```

The model defaults to `sonnet` (Anthropic). For any other provider, pin the
endpoint at scaffold time — all four fields move together, so naming the model is
not optional:

```bash
make workspace-agent \
  AGENT_MODEL=azure:<deployment> \
  AGENT_API_URL=https://<resource>.cognitiveservices.azure.com/ \
  AGENT_API_VERSION=2024-12-01-preview
```

That writes an `[agent]` block into `.dlt/config.toml`, leaving `AGENT__API_KEY`
as the only value anyone supplies. Ask internally for the values; they are
deliberately not committed here.

Switch loops with `AGENT_DEMO_LOOP=claude-agent-sdk`. It is Anthropic-only, but
it reaches an ambient Claude Code login, so it runs locally with no key.
