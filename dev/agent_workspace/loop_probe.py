"""Smallest possible agent: no tools, no platform access, one turn.

Isolates "can the loop authenticate" from every other failure mode.
"""

import asyncio
import os

from dlt.hub.run import TAgentOutput, TJobRunContext, agent

PROBE_LOOP = os.getenv("AGENT_DEMO_LOOP", "pydantic-ai")


@agent(loop=PROBE_LOOP, limits={"max_turns": 1}, expose={"display_name": "Loop auth probe"})
def loop_probe(run_context: TJobRunContext = None) -> TAgentOutput:
    """Reply with the single word `reachable` as your summary, and status `succeeded`.

    Call no tools. Do nothing else.
    """
    return asyncio.run(run_context["ai_loop"].run())
