# Agent jobs workspace

Dev-only workspace for the background agents hackathon. `make workspace-agent`
from the repo root scaffolds it into `examples/agent-workspace` and pins
`api.dlthub.dev`.

It lives outside `src/` on purpose: it pins a **prerelease** `dlt` that carries
the agent launcher, which must not ship in the published wheel.

## Setup

```bash
make workspace-agent                 # scaffolds, syncs, installs the toolkit
cd examples/agent-workspace
export AGENT__API_KEY=sk-ant-...     # the loop needs a key, locally too
uv run dlthub local run loop_probe   # smoke test
```

If `loop_probe` prints `reachable`, your machine is ready.

Then connect and deploy:

```bash
uv run dlthub login
uv run dlthub workspace connect
uv run dlthub deploy
uv run dlthub run jobs.agent_demo.broken_ingest --follow
```

`broken_ingest` fails on purpose. Both agents are triggered by that failure and
start on their own.

## The two tracks

| | file | what you do |
|---|---|---|
| **A. Verified agent** | `verified_agent.py` | nothing to write. Run it, read the diagnosis, evaluate it |
| **B. Your own agent** | `my_agent.py` | edit it. Docstring is the prompt, parameters are the inputs, return type is the output |

Track A runs `dlthub-platform:job-inspector` from the workbench: its prompt,
tools, skills and output schema all come from its `AGENT.md`. Track B defines
the same three things in Python instead. Both deploy together, so a group can
do A first and use it as a reference for B.

Writing an `AGENT.md` rather than Python, or an agent skill, is documented in
`BACKGROUND_AGENTS.md` in the dltHub AI harness.

## The other jobs

| job | needs a key | needs the platform | answers |
|---|---|---|---|
| `loop_probe` | yes | no | can the loop authenticate at all |
| `endpoint_report` | no | no | which endpoint resolved, and whether `AGENT__*` arrived |
| `broken_ingest` | no | no | fails on purpose, to fire the triggers |

Switch loops per shell, default `pydantic-ai`:

```bash
AGENT_DEMO_LOOP=claude-agent-sdk uv run dlthub local run loop_probe
```

`claude-agent-sdk` runs Claude Code, so it takes Anthropic models only, but it
can use an ambient `claude` login instead of a key. `pydantic-ai` serves every
provider and always needs one.

## Model keys

By default a run uses the agent's own model (`sonnet`, Anthropic) and needs only
a key:

```bash
export AGENT__API_KEY=<key>                          # local runs
uv run dlthub variable set AGENT__API_KEY --value <key> --secret --workspace   # deployed
```

To use another provider, pin the endpoint at scaffold time. All four fields move
together, so the model must be named or the key goes to Anthropic:

```bash
make workspace-agent \
  AGENT_MODEL=azure:<deployment> \
  AGENT_API_URL=https://<resource>.cognitiveservices.azure.com/ \
  AGENT_API_VERSION=2024-12-01-preview
```

That writes an `[agent]` block into the workspace's `.dlt/config.toml`, leaving
`AGENT__API_KEY` as the only value anyone supplies. Ask internally for the values
to use; they are deliberately not committed here.

Three things that cost time to discover, all verified against Azure OpenAI:

- **`api_version` is required**, even though Azure's v1 GA API no longer needs
  it. pydantic-ai raises `UserError: Must provide the api_version argument`
  before it sends anything.
- **The endpoint is the `cognitiveservices` URL**, not a Foundry project URL.
  `AzureProvider` wraps `AsyncAzureOpenAI`.
- **`AGENT__MODEL` names the Azure *deployment*,** not the underlying model.

`claude-agent-sdk` is Anthropic-only but reaches an ambient Claude Code login, so
`AGENT_DEMO_LOOP=claude-agent-sdk` runs locally with no key at all.

## State, as of 2026-09-17

Verified against `dlt 1.30.1a0`, `dlthub-client 0.28.5a1`, `pydantic-ai-slim 2.43.0`,
`claude-agent-sdk 0.2.153`.

Working:

- `make workspace-agent` from an empty checkout to a deployed workspace in three
  commands.
- `dlthub deploy` accepts a `background_agent` manifest.
- A `job.fail` trigger starts both agents on the runner, unprompted.
- `AGENT__API_KEY` set as a workspace variable reaches the run and resolves as
  `agent.api_key`; the loop reaches the provider it names.
- **Track A end to end, locally**: `job-inspector` read a real failed run on dev
  over `dlthub_get_run`, `dlthub_get_run_logs`, `dlthub_get_job` and
  `dlthub_list_runs`, loaded the `debug-deployment` skill, and returned a correct
  `classification: config` diagnosis with cited evidence. No API key: the
  `claude-agent-sdk` loop used an ambient Claude Code login.

Blocked, and not by anything in this workspace:

- **An agent job deployed to dev gets no platform identity**, so every platform
  tool fails unauthenticated and the agent aborts. The deployed runtime grants an
  identity only to a job tagged `_unsafe_inject_identity`
  (`dlt_runtime_common/const.py`). dlt-hub/runtime#2109 replaces that check with
  `expose.category == "background_agent"`, which `run.agent` already sets, so
  these jobs need no change once it is merged **and deployed to dev**.

## Why the toolkit agent is copied in by hand

`make workspace-agent` runs `scripts/place_toolkit_agents.py` after installing
the toolkit. That is a workaround, not a step anyone should need.

`dlthub ai toolkit install` installs a toolkit's skills, rules and commands but
never its agents. dlt looks for them at `<toolkit>/agents/`
(`dlt/_workspace/cli/dlthub/ai/commands.py`), while the workbench ships them at
`<toolkit>/dlthub/agents/`. The directory it checks does not exist, so the block
is skipped and nothing is logged: the install reports success, and the failure
surfaces only later as

    Cannot resolve agent 'dlthub-platform:job-inspector'.
    Toolkit 'dlthub-platform' is not installed in this workspace.

which is misleading, because the toolkit is installed.

The script copies the agent folders out of the clone the installer already made,
into `.claude/dlthub/agents/` where the installer would have put them.
`verified_agent.py` therefore uses the ordinary `<toolkit>:<agent>` reference and
needs no change once dlt is fixed: delete the script and its Makefile line.

## Things that will bite

- **The two pins carry the agent support.** `dlt==1.30.1a0` is the prerelease cut
  from `feat/background-agent-launcher` (dlt-hub/dlt#4417); no stable dlt has
  `run.agent`. `dlthub-client==0.28.5a1` carries the platform MCP tools, nothing
  pulls it transitively, and the released `0.28.4` predates them *at a higher
  version number*, so both pins have to be exact.
- **Both pins are prereleases.** Move to the stable versions once #4417 lands and
  dlt cuts 1.30.1. Do not swap either for a branch archive: a branch moves under
  everyone who has already synced.
- **`fastmcp` has to be asked for.** It rides `dlthub[mcp]`. Without it the MCP
  server never starts and the agent silently has no tools.
- **The pydantic-ai floor is load-bearing.** dlt's `agent` group carries no
  minimum; the resolver then walks back to 0.2.4, which has no `ToolFailed`.
  Both failures surface as a `MissingDependencyException` naming a package that
  is already installed.
- **`access` must keep `context: ["read"]`.** Every platform tool declares it;
  drop it and the agent gets no platform tools, with no error.
- **`uv` caches the index.** A just-published version can resolve as "no version
  of ..."; `uv sync --refresh-package dlthub-client` fixes it.
