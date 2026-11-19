---
paths:
  - "**/*.py"
---

# Docstring rules

- DO NOT state the obvious, do not document your thought process

Google style docstrings throughout. `dlthub-init` is a CLI without a public Python API, so the short form is the default.

## Short form (default)
Description only, no Args/Returns. One line saying what the function does or returns.

```python
def build_steps(options: InitOptions, dlt_version: Version) -> list[DlthubStep]:
    """The `dlthub` commands that create the workspace with `options` on `dlt_version`."""
```

## Full form
Only when the signature and one line don't tell the caller enough. Full Google style with Args, Returns, Raises. Describe WHAT the function does and its output, never HOW it works internally.

```python
def run_uv_sync(uv_executable: str, project_dir: Path, *, verbose: bool = False) -> None:
    """Installs the workspace dependencies with `uv sync`.

    Args:
        uv_executable (str): The uv executable to run.
        project_dir (Path): The workspace that holds the dependency file.
        verbose (bool): Show uv's output live instead of capturing it.

    Raises:
        UvError: If uv cannot start or `uv sync` fails. The message carries uv's output.
    """
```

- Args use `name (Type):` format
- Args descriptions are short -- one line unless truly complex
- Use `Yields:` for generators, `Returns:` for regular functions
- `Raises:` only for exceptions the caller should handle
- `Example:` section is optional, add only when usage is non-obvious

## Field and constant docstrings
Inline triple-quoted string on the NEXT line after the field or module constant.

```python
@dataclass(frozen=True)
class InitOptions:
    agent: str | None = None
    """Name of the coding agent, `None` to detect it."""

AGENT_INIT_MIN_DLT = "1.33.0a2"
"""First dlt whose `dlthub init` sets up the coding agent and merges into existing projects."""
```

- Only document fields where the name + type aren't self-explanatory
- Keep to one line when possible

## Inline formatting
Docstrings are rendered as Markdown by most editors. Use only these:
- Single backticks for parameter names, values, types, paths, commands: `name`, `True`, `None`, `uv sync`
- **bold** for emphasis on key terms
- `Note:` or `Warning:` prefixes for callouts in prose

Do NOT use:
- Double backticks ``like this`` (reStructuredText literal)
- `:param:`, `:type:`, `:returns:`, `:rtype:` (Sphinx field list)
- `.. directive::` blocks (reST directives)

## Anti-patterns -- NEVER do these
- Do not explain HOW the code works, only WHAT it does and its output
- Do not state the obvious (`"""Returns the name"""` on `get_name`)
- Do not add docstrings to code you did not change
- Do not use restructured text/sphinx formatting (see Inline formatting above)
