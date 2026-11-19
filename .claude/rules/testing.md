---
paths:
  - "tests/**/*.py"
  - "tests_integration/**/*.py"
---

# Testing

## Style and structure
- Module-based tests (plain `def test_*() -> None:` functions), not class-based
- pytest with fixtures in `conftest.py`, not unittest setUp/tearDown

## Reduce tests sprawl
- Use `pytest.mark.parametrize` to reduce code duplication. ALWAYS use human readable ids for the test cases
- It is OK to test many related use cases in one test: ie. when they share common setup or represent a flow of user actions

## Fixtures
- `tests/conftest.py` has an autouse fixture that clears the PostHog key and resets the telemetry state, so no test sends a real event. Check it before adding fixtures that preserve env variables or module state
- Use `monkeypatch` for env variables and module attributes, `tmp_path` for files

## Unit and integration tests
- `tests/` are unit tests. They never start `dlthub` or `uv`: mock `run_step`, `run_uv_sync` and the executable lookups where the calling module imports them
- `tests_integration/` run the real CLI: `dlthub init`, the agent setup and `uv sync`. They need uv and network access
- Tests write only to `tmp_path`, never to the repo or to the user's `~/.dlt`

## Platforms
- CI runs all tests on Linux, macOS and Windows. Build paths with `pathlib`, join PATH entries with `os.pathsep`, and keep local path assertions Windows compatible

## Placement and comments
- When adding new test ALWAYS try find the right place by looking where code you make changes is tested
- Docstrings: DESCRIBE test case. SKIP when test name is sufficient
- Use line comments to describe and separate use cases within a single test

## Running
- `make test` runs the unit tests, `make test-integration` the integration tests
- DO NOT start two `pytest` processes at once!
