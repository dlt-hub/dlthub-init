"""Track B: write your own agent. Edit this file.

Three things define the agent, and all three are ordinary Python:

    docstring    -> the system prompt, with `{{ placeholders }}` for the inputs
    parameters   -> the inputs, and so the job's configuration keys
    return type  -> the output schema the model must fill

`run_context` is passed by the launcher; it is not an input and needs no default
beyond `None`. The other form, an `AGENT.md` file, is documented in
BACKGROUND_AGENTS.md in the dltHub AI harness.
"""

import asyncio
import os
from typing import Literal

from dlt.common.typing import Annotated, Doc
from dlt.hub.run import Entity, TAgentOutput, TJobRunContext, agent

from jaffle_shop.bad_incremental import load_jaffle_bad_incremental

AGENT_LOOP = os.getenv("AGENT_DEMO_LOOP", "pydantic-ai")
"""The loop that runs the model. `pydantic-ai` serves every provider and always
needs a key; `claude-agent-sdk` is Anthropic-only and can reach an ambient Claude
Code login instead. Override per shell rather than editing this file."""


class CrashReport(TAgentOutput):
    """`status` and `summary` come from the base. Add whatever else you want back.

    Descriptions are not decoration: the model reads them when it fills a field.
    """

    # `Entity` marks this as a workspace entity rather than a plain string, so the
    # run reports it in `object` and shows up on that run's page in the web UI.
    failed_run_id: Annotated[str, Entity("job-run"), Doc("The run this agent was triggered by")]
    classification: Annotated[
        Literal["config", "code", "upstream_data", "unknown"],
        Doc("What kind of failure it was"),
    ]
    confidence: Annotated[Literal["high", "medium", "low"], Doc("How sure you are")]


@agent(
    loop=AGENT_LOOP,
    # dlthub MCP feature groups. The loop passes --no-default-features, so the
    # agent gets exactly these and nothing else.
    tools=["jobs", "logs"],
    # Every platform tool requires `context: read`. Drop it and the agent is
    # served no platform tools, with no error to tell you so.
    access={"local": ["read"], "data": ["read"], "context": ["read"]},
    trigger=[load_jaffle_bad_incremental.fail],
    limits={"max_turns": 30},
    expose={"display_name": "My agent"},
)
def my_agent(
    # Every input is a job configuration key (`-c failed_run_id=...`). The first
    # entity-typed one also becomes `expose.object_input`, which is how the web UI
    # offers this agent from a failed run's row. Not required: a `job.fail` trigger
    # supplies nothing, and a required input with no value fails the run.
    failed_run_id: Annotated[str, Entity("job-run")] = "",
    run_context: TJobRunContext = None,
) -> CrashReport:
    """Diagnose the run that triggered you. Do not repair anything.

    Investigate run `{{ failed_run_id }}`. It is usually empty, because a
    `job.fail` trigger names the job that failed but not the run. Find it:

    1. `dlthub_get_run` on your own run id, `{{ run_context.run_id }}`. Its
       `prev_run_id` is the run that failed. Report it as `failed_run_id`.
    2. `dlthub_get_run` on that id for its status, then `dlthub_get_run_logs`
       for the traceback. Classify the cause and say how sure you are.

    Explain the failure in `summary`. Do not trigger any run.
    """
    # `inputs=` by keyword: the first positional argument is `instructions`.
    return asyncio.run(run_context["ai_loop"].run(inputs={"failed_run_id": failed_run_id}))
