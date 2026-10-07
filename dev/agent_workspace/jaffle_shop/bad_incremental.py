"""BROKEN #3 — wrong incremental cursor. Fails once extraction starts.

The orders endpoint accepts `start_date` / `end_date`, and each order carries
an `ordered_at` timestamp. This job configures the incremental cursor on
`updated_at` — a field that does not exist on this API.

Expected failure:
    IncrementalCursorPathMissing: Cursor element with JSON path `updated_at`
    was not found in extracted data item.

The tell is that it fails *during* extraction rather than on the first request,
so unlike the 404 case it can leave a partial load behind. Fix by pointing
`cursor_path` at the real field, `ordered_at`.
"""

import dlt
from dlt.hub import run
from dlt.hub.run import trigger
from dlt.sources.rest_api import rest_api_source

from jaffle_shop import BASE_URL, DATASET, PAGE_SIZE, TAG


def bad_incremental_source():
    return rest_api_source(
        {
            "client": {"base_url": BASE_URL, "paginator": "header_link"},
            "resources": [
                {
                    "name": "orders_bad_incremental",
                    "primary_key": "id",
                    "write_disposition": "merge",
                    "endpoint": {
                        "path": "orders",
                        "params": {
                            "page_size": PAGE_SIZE,
                            "start_date": {
                                "type": "incremental",
                                # BUG: orders have `ordered_at`, not `updated_at`
                                "cursor_path": "updated_at",
                                "initial_value": "2017-01-01",
                            },
                        },
                    },
                },
            ],
        }
    )


@run.pipeline(
    "jaffle_bad_incremental",
    section="jaffle_shop",
    trigger=trigger.tag(TAG),
    expose={
        "display_name": "Jaffle — BROKEN incremental cursor",
        "tags": ["jaffle", "broken", "fails"],
    },
)
def load_jaffle_bad_incremental() -> None:
    """Always fails with IncrementalCursorPathMissing on `updated_at`."""
    pipeline = dlt.pipeline(
        pipeline_name="jaffle_bad_incremental",
        destination="playground",
        dataset_name=DATASET,
    )
    info = pipeline.run(bad_incremental_source())
    print(info)


if __name__ == "__main__":
    load_jaffle_bad_incremental()
