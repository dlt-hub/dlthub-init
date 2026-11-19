# dlthub-init (beta)

Create a [dltHub](https://dlthub.com) workspace in a new or existing directory and set up your coding agent.

`dlthub-init` runs `dlthub init` from the newest dlt, then installs the dependencies with `uv sync`. It ships no
workspace files of its own: the workspace files, the dependencies and the skills, rules and MCP server of your coding
agent all come from dlt, so they are always current.

## Usage

```bash
uvx dlthub-init@latest                 # initialize the current directory
uvx dlthub-init@latest my-workspace    # initialize ./my-workspace, created when missing
uvx dlthub-init@latest --agent cursor  # name the coding agent instead of detecting it
```

`@latest` makes uv resolve the newest `dlthub-init` and the newest dlt on every run.

The coding agent is always set up. Inside a Claude Code, Cursor, Codex or Cortex Code session it is detected, so you
don't need `--agent`. Outside a session, dlt picks the agent installed for your user. If it finds none, or more than
one, it stops and asks for `--agent`.

In an existing project, `dlthub init` merges into your files. It lists the existing files it changes and the lines it
adds, then asks whether to proceed. `-y` applies the changes without asking. Without a terminal and without `-y`, it
changes nothing and exits with an error, so an agent can show you the list first and re-run with `-y`.

### Options

These options are passed on to `dlthub init`:

| Option | Effect |
| --- | --- |
| `--name NAME` | Workspace name. Defaults to the directory name. |
| `--overwrite` | Overwrite the dependency file, `.gitignore` and `.dlt/.workspace` instead of merging into them. Asks first on dlt 1.33.0 or newer. Settings files are never overwritten. |
| `--skip` | Keep existing files as they are and create only the missing ones, without asking. |
| `--dependencies {auto,pyproject,requirements}` | Dependency file to create. |
| `--dry-run` | Print the plan without writing anything. |
| `--agent NAME` | Coding agent to set up: `claude`, `cursor`, `codex` or `cortex`. Detected when omitted. |
| `-y`, `--yes` | Apply the changes to existing files without asking. |

These belong to `dlthub-init`:

| Option | Effect |
| --- | --- |
| `DIR` | Directory to initialize, created when missing. Defaults to the current directory. |
| `--no-sync` | Don't install the dependencies with `uv sync`. |
| `--no-telemetry` | Disable usage telemetry for this run, also in the `dlthub` commands it runs. |
| `-v`, `--verbose` | Show the output of `uv sync`. |

## Output

`dlthub-init` shows the full output of `dlthub init`: the plan with each file it creates, keeps, merges or overwrites,
the confirmation when existing files change, the agent setup and dlt's next steps. Then it installs the dependencies
behind a spinner and prints what to do next. When `uv sync` fails, its output is shown and the workspace stays as
`dlthub init` left it.

## dlt versions

`dlthub-init` uses the newest dlt that uv resolves, which is the newest stable release.

| dlt | What runs |
| --- | --- |
| 1.33.0 or newer | `dlthub init --agent`, which merges into existing projects |
| 1.27.2 to 1.32.x | `dlthub init`, then `dlthub ai init`. Nothing is merged: existing files are kept, an existing workspace only gets the agent setup, and `--overwrite` maps to `--force` |

1.33.0a2 is the first pre-release that merges. The pre-releases 1.33.0a0 and 1.33.0a1 run as in the second row. To
try a dlt pre-release:

```bash
uvx --prerelease allow dlthub-init@latest
uvx --with "dlt==<version>" dlthub-init@latest
```

## Telemetry

`dlthub-init` sends anonymous usage events so we can improve the setup experience.

No personal data is collected, and no workspace contents are ever sent.

Telemetry is controlled by the following, in order of precedence:

1. the `--no-telemetry` flag,
2. `DLTHUB_INIT_TELEMETRY=0` (or `false`/`off`),
3. `DO_NOT_TRACK=1`,
4. an existing dlt opt-out (`~/.dlt/config.toml` `[runtime] dlthub_telemetry = false`,
   or `RUNTIME__DLTHUB_TELEMETRY=false`).

The first three also turn dlt's telemetry off in the `dlthub` commands that `dlthub-init` runs, for this run only.

## Development

```bash
make dev      # install dev dependencies
make lint     # ruff + mypy
make test     # unit tests
make ci       # full local CI
```

## Releasing

You run two `make` targets on your machine. In between, GitHub creates the tag and the release when you merge.

```bash
# on your machine, on a clean devel that matches origin/devel, logged in with gh
make prepare-release              # LEVEL=minor or LEVEL=major for a bigger bump
# review and merge the release pull request on GitHub, then
git fetch --tags && git checkout vX.Y.Z
make publish                      # needs the PostHog key in .make.env, see CONTRIBUTING.md
```

1. `make prepare-release` (your machine) works out the new version with `uv version --bump --dry-run`, checks that
   neither its tag nor its release branch exists and no release pull request is open, and shows the commits since the
   last release, stopping when there are none. After you confirm, it bumps the version with `uv version --bump`, commits
   `chore: bump version to X.Y.Z` on a new branch `chore/release-vX.Y.Z`, pushes it and opens a pull request labelled
   `release`, which starts CI. You stay on the release branch, also when a step fails.
2. You merge the pull request when CI passes. The `release` workflow (GitHub) tags the merge commit `vX.Y.Z` and
   creates the GitHub release.
3. `make publish` (your machine) uploads the tagged version to PyPI.

There is no changelog file. GitHub generates the release notes from the titles of the pull requests merged since the
last release, so write those titles as [Conventional Commits](https://www.conventionalcommits.org/).
