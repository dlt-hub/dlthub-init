.DEFAULT_GOAL := help

.PHONY: help dev lint lint-fix format format-check fl lint-ci test test-integration build clean-dist version-upgrade version-upgrade-patch version-upgrade-minor version-upgrade-major prepare-release require-posthog-key publish ci lock-upgrade lock-check workspace workspace-init

PYTHON_SOURCES := src tests tests_integration

-include .make.env
export DLTHUB_INIT_POSTHOG_KEY

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

dev: ## Install dev dependencies
	uv sync --extra dev

lint: ## Lint with ruff and type-check with mypy
	uv run ruff check $(PYTHON_SOURCES)
	uv run mypy $(PYTHON_SOURCES)

lint-fix: ## Lint and autofix with ruff, type-check with mypy
	uv run ruff check --fix $(PYTHON_SOURCES)
	uv run mypy $(PYTHON_SOURCES)

format: ## Format with ruff
	uv run ruff format $(PYTHON_SOURCES)

format-check: ## Check formatting with ruff (no writes)
	uv run ruff format --check $(PYTHON_SOURCES)

fl: format lint-fix ## Format and lint-fix in one shot

lint-ci: format-check lint ## CI lint workflow (format-check then lint)

test: ## Run unit tests (fast)
	uv run pytest tests

test-integration: ## Run e2e integration tests (slow; runs dlthub init, the agent setup and uv sync)
	uv run pytest tests_integration

WORKSPACE_DIR ?= examples/my-workspace

workspace: dev ## Create a fresh ./$(WORKSPACE_DIR) for eyeballing output (pre-deletes; pass ARGS="--no-sync --agent claude")
	@case "$(WORKSPACE_DIR)" in *..*|"") echo "invalid WORKSPACE_DIR: $(WORKSPACE_DIR)"; exit 1;; esac
	rm -rf -- "$(WORKSPACE_DIR)"
	uv run dlthub-init "$(WORKSPACE_DIR)" $(ARGS)

WORKSPACE_INIT_DIR ?= examples/init-workspace

workspace-init: dev ## Init in place: make empty ./$(WORKSPACE_INIT_DIR), cd in, run the CLI with no positional (pass ARGS="--no-sync")
	@case "$(WORKSPACE_INIT_DIR)" in *..*|"") echo "invalid WORKSPACE_INIT_DIR: $(WORKSPACE_INIT_DIR)"; exit 1;; esac
	rm -rf -- "$(WORKSPACE_INIT_DIR)"
	mkdir -p -- "$(WORKSPACE_INIT_DIR)"
	cd "$(WORKSPACE_INIT_DIR)" && "$(CURDIR)/.venv/bin/dlthub-init" $(ARGS)

build: dev ## Build the package wheel
	uv build

clean-dist: ## Remove dist/ directory
	-@rm -r dist/

version-upgrade: ## Bump version in pyproject.toml + uv.lock. Prompts when interactive, else pass LEVEL=major|minor|patch (or use version-upgrade-{patch,minor,major})
	@level="$(LEVEL)"; \
	if [ -z "$$level" ]; then \
		if [ -t 0 ]; then \
			echo "Current version: $$(uv version --short)"; \
			printf "Bump which part? [major/minor/patch] "; \
			read level; \
		else \
			echo "error: no TTY for the prompt — pass LEVEL=major|minor|patch or run 'make version-upgrade-patch'"; exit 1; \
		fi; \
	fi; \
	case "$$level" in \
		major|minor|patch) ;; \
		*) echo "error: expected major, minor, or patch (got '$$level')"; exit 1;; \
	esac; \
	uv version --bump "$$level" --no-sync; \
	echo "version-upgrade: updated pyproject.toml and uv.lock — review 'git diff pyproject.toml uv.lock' and commit."

version-upgrade-patch: ## Bump the patch version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=patch

version-upgrade-minor: ## Bump the minor version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=minor

version-upgrade-major: ## Bump the major version non-interactively (AI/CI-friendly)
	@$(MAKE) version-upgrade LEVEL=major

prepare-release: LEVEL ?= patch
prepare-release: ## Open the release pull request for origin/devel after a confirmation (LEVEL=patch|minor|major, default patch)
	@set -e; \
	case "$(LEVEL)" in major|minor|patch) ;; *) echo "prepare-release: LEVEL must be major, minor or patch, got '$(LEVEL)'"; exit 1;; esac; \
	if [ "$$(git branch --show-current)" != "devel" ]; then echo "prepare-release: switch to devel first"; exit 1; fi; \
	if [ -n "$$(git status --porcelain)" ]; then echo "prepare-release: the working tree has changes, commit or stash them first"; exit 1; fi; \
	gh auth status >/dev/null 2>&1 || { echo "prepare-release: log in with 'gh auth login' first"; exit 1; }; \
	git fetch --quiet --tags origin; \
	if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse origin/devel)" ]; then echo "prepare-release: devel is not at origin/devel, pull or push first"; exit 1; fi; \
	open=$$(gh pr list --label release --state open --json number --jq 'map("#\(.number)") | join(", ")'); \
	if [ -n "$$open" ]; then echo "prepare-release: release pull request $$open is open, merge or close it first"; exit 1; fi; \
	current=$$(uv version --short); \
	version=$$(uv version --bump "$(LEVEL)" --dry-run --short); \
	previous=$$(git describe --tags --abbrev=0 --match 'v*'); \
	branch="chore/release-v$$version"; \
	if git rev-parse -q --verify "refs/tags/v$$version" >/dev/null; then echo "prepare-release: tag v$$version exists locally"; exit 1; fi; \
	if [ -n "$$(git ls-remote --tags origin "refs/tags/v$$version")" ]; then echo "prepare-release: tag v$$version exists on origin"; exit 1; fi; \
	if [ -n "$$(git ls-remote --heads origin "$$branch")" ]; then echo "prepare-release: branch $$branch exists on origin"; exit 1; fi; \
	if [ "$$(git rev-list --count "$$previous..HEAD")" = "0" ]; then echo "prepare-release: nothing to release, devel has no commits since $$previous"; exit 1; fi; \
	echo "Release $$current -> $$version from origin/devel at $$(git log -1 --format='%h %s')"; \
	echo "Commits since $$previous:"; \
	git log --no-merges --format='  %h %s' "$$previous..HEAD"; \
	echo "This will:"; \
	echo "  - run uv version --bump $(LEVEL) and commit 'chore: bump version to $$version' on a new branch $$branch"; \
	echo "  - push $$branch and open a pull request labelled 'release' into devel, which starts CI"; \
	echo "You stay on $$branch."; \
	echo "Merging the pull request tags its merge commit v$$version and creates the GitHub release."; \
	printf "Proceed? [y/N] "; \
	read -r answer || true; \
	case "$$answer" in y|Y|yes) ;; *) echo "prepare-release: cancelled"; exit 1;; esac; \
	body=$$(mktemp); \
	{ \
		echo "Merging this pull request tags its merge commit \`v$$version\` and creates the GitHub release with notes generated from the pull requests merged since \`$$previous\`."; \
		echo; \
		echo "### Commits since $$previous"; \
		echo; \
		git log --no-merges --format='- %s (%h)' "$$previous..HEAD"; \
	} > "$$body"; \
	trap 'rm -f "$$body"' EXIT; \
	git switch -q -c "$$branch"; \
	uv version --bump "$(LEVEL)" --no-sync; \
	git commit -q -am "chore: bump version to $$version"; \
	git push -q origin "$$branch"; \
	gh label create release --color 0E8A16 --description "Merging creates the GitHub release" --force >/dev/null; \
	gh pr create --base devel --head "$$branch" --label release --title "chore: bump version to $$version" --body-file "$$body"

require-posthog-key:
	@case "$(DLTHUB_INIT_POSTHOG_KEY)" in \
		phc_*) ;; \
		*) echo "publish: DLTHUB_INIT_POSTHOG_KEY not set (or not a phc_ key) — add it to .make.env"; exit 1;; \
	esac

publish: require-posthog-key clean-dist build ## Build and publish dlthub-init to PyPI
	ls -l dist/
	@bash -c 'read -s -p "Enter PyPI API token: " PYPI_API_TOKEN; echo; \
	uv publish --token "$$PYPI_API_TOKEN"'

lock-upgrade: ## Upgrade the root uv.lock to the latest deps pyproject.toml allows (PKG=<name> to bump one); review the diff and commit
	uv lock $(if $(PKG),--upgrade-package $(PKG),--upgrade)

lock-check: ## CI guard: fail if the root uv.lock is out of sync with pyproject.toml
	@echo "lock-check: checking uv.lock against pyproject.toml…"; \
	log="$$(mktemp)"; \
	if uv lock --check >"$$log" 2>&1; then \
		rm -f "$$log"; \
		echo "lock-check: OK — uv.lock is in sync with pyproject.toml."; \
	else \
		echo "lock-check: FAILED — run 'make lock-upgrade' and commit. uv output:"; \
		cat "$$log"; rm -f "$$log"; \
		exit 1; \
	fi

ci: lint-ci test test-integration lock-check build ## Run all CI checks locally
