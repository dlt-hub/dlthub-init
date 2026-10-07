"""Records that a job failed. The starting point for Track B.

It knows *that* something broke, from the trigger that woke it. It cannot say
*why*, because a trigger carries no logs, no traceback and no row counts.
Turning this into an agent is the exercise.
"""

from datetime import datetime, timezone

import dlt
from dlt.hub import run
from dlt.hub.run import TJobRunContext

from jaffle_shop import DATASET
from jaffle_shop.bad_config import load_jaffle_bad_config
from jaffle_shop.bad_incremental import load_jaffle_bad_incremental

WATCHED = (load_jaffle_bad_config, load_jaffle_bad_incremental)
"""The two jaffle jobs that fail outright. The other two run green, so nothing
triggers on them — finding those is Track B's real problem."""

FAILED_JOB_BY_TRIGGER = {job.fail: job.job_ref for job in WATCHED}


@run.job(
    trigger=[job.fail for job in WATCHED],
    # No "jaffle" tag: `dlthub job trigger tag:jaffle` selects on expose tags too,
    # and this job should only ever wake on a failure.
    expose={"display_name": "Alerts (on any failure)", "tags": ["alerting"]},
)
def alerts(run_context: TJobRunContext) -> None:
    """Write one row naming the job that failed and the trigger that woke this one."""
    fired_by = run_context["trigger"]
    failed_job = FAILED_JOB_BY_TRIGGER.get(fired_by, fired_by)

    alert = {
        "alert_id": run_context["run_id"],
        "failed_job": failed_job,
        "trigger": fired_by,
        "message": f"{failed_job} failed — check `dlthub job logs {failed_job.rsplit('.', 1)[-1]}`",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"ALERT: {alert['message']}")

    pipeline = dlt.pipeline(pipeline_name="jaffle_alerts", destination="playground", dataset_name=DATASET)
    print(pipeline.run([alert], table_name="alerts", write_disposition="append"))
