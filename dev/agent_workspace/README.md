# Agent jobs workspace

Dev-only workspace for the background agents hackathon: five pipelines that fail
in four different ways, and two agents that diagnose them.

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

Only the two that fail wake an agent. **The two green ones lose data without
failing**, so no job-status trigger can see them. Catching those means comparing
row counts against `correct`.

## The two tracks

| | file | what you do |
|---|---|---|
| **A. Verified agent** | `verified_agent.py` | nothing to write. Run it, judge the diagnosis, and find what it cannot see |
| **B. Your own agent** | `my_agent.py` | edit it. Docstring is the prompt, parameters are the inputs, return type is the output |

`alerts.py` is where Track B starts: it fires on failure and records *that*
something broke, but cannot say *why*, because a trigger carries no logs or counts.

`my_agent.py` is a working agent, not a blank template. Copy its shape — the
`access`, `tools` and `Entity` declarations are all load-bearing.

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
