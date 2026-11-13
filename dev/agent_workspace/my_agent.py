"""Step 2: write your own agent. Start here.

Copy `example_agent.py` and change it, or write from scratch. The shape:

    docstring    -> the system prompt
    parameters   -> the inputs
    return type  -> the output schema

Pick something the workspace cannot do yet:

- `alerts.py` records *that* a job failed, never *why*. A trigger carries no
  logs, no traceback, no row counts.
- Nothing wakes for `bad_pagination` or `bad_selector`. They finish **green**
  while loading a fraction of the rows, so a `job.fail` trigger cannot see them.
  Triggers also come in `.success`.

Then import it in `__deployment__.py`, add it to `__all__`, and deploy.
"""
