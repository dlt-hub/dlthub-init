"""Jaffle Shop demo — one correct pipeline against a real API, and four broken ones.

Live API: https://jaffle-shop.dlthub.com/docs  (OpenAPI: /openapi.json)

Pagination contract, straight from the spec:
    "Pagination is controlled via the `page` query parameter. Each page returns
     a fixed number of results (see `page_size`). If more results are available,
     the response will include a `Link` header with rel="next"."

So the *correct* paginator is `header_link`. Every list endpoint returns a bare
JSON array — there is no envelope and no `next` key in the body.

Ground truth from GET /api/v1/row-counts (checked 2026-09-17):
    customers    935
    orders    61,948
    items     90,900
    products      10
    stores         6
    supplies      65
"""

BASE_URL = "https://jaffle-shop.dlthub.com/api/v1/"
DATASET = "jaffle_shop"
PAGE_SIZE = 100

# Fires every job that declares `trigger.tag("jaffle")`:
#   uv run dlthub job run "tag:jaffle"
TAG = "jaffle"
