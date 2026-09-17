"""Track B: write your own agent. Edit this file.

Three things define the agent, and all three are ordinary Python:

    docstring    -> the system prompt, with `{{ placeholders }}` for the inputs
    parameters   -> the inputs, and so the job's configuration keys
    return type  -> the output schema the model must fill

`run_context` is passed by the launcher and is not an input. The other form, an
`AGENT.md` file, is documented in BACKGROUND_AGENTS.md in the dltHub AI harness.
"""

import asyncio
import os
from typing import Literal

from dlt.common.typing import Annotated, Doc
from dlt.hub.run import Entity, TAgentOutput, TJobRunContext, agent

from jaffle_shop.bad_incremental import load_jaffle_bad_incremental

AGENT_LOOP = os.getenv("AGENT_DEMO_LOOP", "pydantic-ai")
"""Loop to run the model on. Override per shell; see the README."""


class CrashReport(TAgentOutput):
    """What the agent must return. `status` and `summary` come from the base.

    Descriptions are not decoration: the model reads them when it fills a field.
    """

    failed_run_id: Annotated[str, Entity("job-run"), Doc("Run id you diagnosed, as a workspace entity")]
    classification: Annotated[Literal["config", "code", "upstream_data", "unknown"], Doc("What kind of failure it was")]
    confidence: Annotated[Literal["high", "medium", "low"], Doc("How sure you are")]


@agent(
    loop=AGENT_LOOP,
    tools=["jobs", "logs"],  # dlthub MCP feature groups; an allowlist, not a default
    access={"local": ["read"], "data": ["read"], "context": ["read"]},  # `context` serves the tools
    trigger=[load_jaffle_bad_incremental.fail],
    limits={"max_turns": 30},
    expose={"display_name": "My agent"},
)
def my_agent(
    failed_run_id: Annotated[
        str, Entity("job-run"), Doc("Run to diagnose. Empty on a job.fail trigger: find it yourself")
    ] = "",
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
    context = {k: v for k, v in run_context.items() if k != "ai_loop"}
    return asyncio.run(run_context["ai_loop"].run(inputs={"failed_run_id": failed_run_id, "run_context": context}))
