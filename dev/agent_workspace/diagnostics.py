"""Setup checks that need no model key: what endpoint resolved, and what reached the run."""

import os
from typing import Any

from dlt._workspace.deployment.configuration import AgentConfiguration
from dlt.common.configuration import resolve_configuration
from dlt.hub.run import job

_SECRET_WORDS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


def mask(name: str, value: str) -> str:
    """Length only for anything that looks like a credential, so logs stay shareable."""
    if any(word in name.upper() for word in _SECRET_WORDS):
        return f"<set, {len(value)} chars>" if value else "<empty>"
    return value


@job(section="diagnostics", expose={"display_name": "Report the resolved agent endpoint"})
def endpoint_report(run_context: dict[str, Any] = None) -> dict[str, Any]:
    """Reports which model endpoint a run resolved, and whether `AGENT__*` arrived.

    Spends no tokens and needs no key, so it answers "is my key configured and did
    it reach the run" on its own. Set only `AGENT__API_KEY` and `effective_model`
    stays at the agent's default, which is how a key reaches the wrong provider.
    """
    config = resolve_configuration(AgentConfiguration())
    report = {
        "endpoint_source": config.endpoint_source,
        "effective_model": config.effective_model,
        "effective_api_key_set": bool(config.effective_api_key),
        "user_api_url": config.api_url,
        "user_api_version": config.api_version,
    }
    print("--- resolved agent endpoint ---", flush=True)
    for key, value in report.items():
        print(f"  {key}={value}", flush=True)
    agent_env = {n: mask(n, v) for n, v in os.environ.items() if n.upper().startswith("AGENT__")}
    print(f"  AGENT__* in environment: {agent_env or 'none'}", flush=True)
    return report
