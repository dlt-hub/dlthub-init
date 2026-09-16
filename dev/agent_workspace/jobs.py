"""The job the agent investigates, and a credential-free probe of endpoint resolution."""

# Python internals
import os
from typing import Any

# Other libraries
import dlt
from dlt._workspace.deployment.configuration import AgentConfiguration
from dlt.common.configuration import resolve_configuration
from dlt.hub.run import job

_SECRET_WORDS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


def mask(name: str, value: str) -> str:
    """Length only for anything that looks like a credential, so logs stay shareable."""
    if any(word in name.upper() for word in _SECRET_WORDS):
        return f"<set, {len(value)} chars>" if value else "<empty>"
    return value


@job(
    section="agent_demo",
    expose={"display_name": "Broken ingest (fails on purpose)"},
)
def broken_ingest(
    # Left unconfigured: resolving this is what fails the run.
    rows_expected: int = dlt.config.value,
    run_context: dict[str, Any] = None,
) -> str:
    """Loads nothing. Raises before it starts, because `rows_expected` is unset."""
    print(f"broken_ingest starting, run_id={os.getenv('RUNTIME__RUN_ID')}")
    return f"never reached, wanted {rows_expected} rows"


@job(
    section="agent_demo",
    expose={"display_name": "Report the resolved agent endpoint"},
)
def endpoint_report(run_context: dict[str, Any] = None) -> dict[str, Any]:
    """Resolves AgentConfiguration and reports which endpoint a run would use.

    Spends no tokens and needs no model key, so it answers "did `AGENT__API_KEY`
    survive the trip into the run environment" on its own.
    """
    config = resolve_configuration(AgentConfiguration())
    report = {
        "endpoint_source": config.endpoint_source,
        "user_model": config.model,
        "user_api_key_set": bool(config.api_key),
        "user_api_url": config.api_url,
        "runtime_model": config.runtime_model,
        "runtime_api_key_set": bool(config.runtime_api_key),
        "runtime_api_url": config.runtime_api_url,
        "effective_model": config.effective_model,
        "effective_api_key_set": bool(config.effective_api_key),
    }
    print("--- resolved agent endpoint ---", flush=True)
    for key, value in report.items():
        print(f"  {key}={value}", flush=True)

    agent_env = {n: mask(n, v) for n, v in os.environ.items() if n.upper().startswith("AGENT__")}
    print(f"  AGENT__* in environment: {agent_env or 'none'}", flush=True)
    print("--- end resolved agent endpoint ---", flush=True)
    return report
