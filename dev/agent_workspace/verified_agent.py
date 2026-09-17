"""Step 1: set up the verified agent. Write it here.

`job-inspector` is dltHub's verified agent. It ships in the `dlthub-platform`
toolkit, already installed in this workspace, so declaring it as a job is three
lines: the toolkit reference, and a trigger saying when it wakes.

    from dlt.hub.run import agent
    from jaffle_shop.bad_config import load_jaffle_bad_config

    job_inspector = agent(
        "dlthub-platform:job-inspector",
        trigger=[load_jaffle_bad_config.fail],
    )

Pick the pipeline your team is watching. `bad_config` and `bad_incremental`
fail; `bad_pagination` and `bad_selector` finish green. Then add `job_inspector`
to `__deployment__.py`, deploy, and run `dlthub job trigger tag:jaffle`.
"""
