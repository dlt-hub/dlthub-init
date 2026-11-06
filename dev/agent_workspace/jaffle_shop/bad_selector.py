"""BROKEN #4 — wrong data selector. Green run, empty table.

`data_selector` is a JSONPath into the response body. This API returns a bare
array, so the records are at the root. Pointing the selector at `data.results`
— the shape a *different* API would use — matches nothing, so the resource
yields zero records.

    correct (root / omitted)  -> 6 stores
    this    (`data.results`)  -> 0 rows

Same failure class as the pagination bug: the run is green, no exception is
raised, and the only symptom is a table that is emptier than it should be.
A row-count check is what catches this, not the job status.
"""

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import rest_api_source

from jaffle_shop import BASE_URL, DATASET, PAGE_SIZE, TAG


def bad_selector_source():
    return rest_api_source(
        {
            "client": {"base_url": BASE_URL, "paginator": "header_link"},
            "resource_defaults": {
                "write_disposition": "replace",
                "endpoint": {"params": {"page_size": PAGE_SIZE}},
            },
            "resources": [
                {
                    "name": "stores_bad_selector",
                    "endpoint": {
                        "path": "stores",
                        # BUG: response is a bare array — there is no `data.results`
                        # envelope. Omit data_selector entirely to read the root.
                        "data_selector": "data.results",
                    },
                },
            ],
        }
    )


@run.pipeline(
    "jaffle_bad_selector",
    section="jaffle_shop",
    trigger=trigger.tag(TAG),
    expose={
        "display_name": "Jaffle — BROKEN data selector (empty table)",
        "tags": ["jaffle", "broken", "silent"],
    },
)
def load_jaffle_bad_selector() -> None:
    """Succeeds, loads 0 rows instead of 6 stores."""
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_bad_selector",
        destination="playground",
        dataset_name=DATASET,
    )
    info = pipeline.run(bad_selector_source())
    print(info)
    print("NOTE: green run, 0 rows loaded — expected 6 stores.")


if __name__ == "__main__":
    load_jaffle_bad_selector()
