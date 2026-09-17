"""Track A: the verified agent from the dltHub workbench.

Nothing to author. `job-inspector` ships in the `dlthub-platform` toolkit, which
also carries the skill and rules it references. `make workspace-agent` installs
it; see the README for why its folder is copied in by hand.

Everything the agent *is* comes from its AGENT.md: the prompt, the tools, the
inputs and the output schema. What is set here belongs to the job, and a run may
still override it (`agent.model`, `agent.instructions`, `agent.max_turns`).
"""

import os

from dlt.hub.run import agent

from jaffle_shop.bad_config import load_jaffle_bad_config

AGENT_LOOP = os.getenv("AGENT_DEMO_LOOP", "pydantic-ai")
"""The loop that runs the model. `pydantic-ai` serves every provider and always
needs a key; `claude-agent-sdk` is Anthropic-only and can reach an ambient Claude
Code login instead. Override per shell rather than editing this file."""

job_inspector = agent(
    "dlthub-platform:job-inspector",
    loop=AGENT_LOOP,
    trigger=[load_jaffle_bad_config.fail],
    expose={"display_name": "Job inspector (verified)"},
)
