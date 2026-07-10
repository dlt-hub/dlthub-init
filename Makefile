.DEFAULT_GOAL := help

.PHONY: help dev lint lint-fix format format-check fl lint-ci test test-integration build clean-dist version-upgrade version-upgrade-patch version-upgrade-minor version-upgrade-major require-posthog-key publish ci lock-upgrade lock-check scaffold-lock-upgrade scaffold-lock-check generate-skills update-skills check-skills workspace workspace-init workspace-env workspace-local workspace-dev

PYTHON_SOURCES := src tests tests_integration scripts
SCAFFOLD_DIR ?= src/dlthub_init/scaffolds/minimal_workspace

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
	uv run python -m unittest discover -s tests -t .

test-integration: ## Run e2e integration tests (slow; invokes real CLI + uv sync)
	uv run python -m unittest discover -s tests_integration -t .

#
# Manual test workspaces (under examples/, which is gitignored)
#

WORKSPACE_DIR ?= examples/my-workspace

workspace: dev ## Scaffold a fresh ./$(WORKSPACE_DIR) for eyeballing output (pre-deletes; pass ARGS="--no-sync")
	@case "$(WORKSPACE_DIR)" in *..*|"") echo "invalid WORKSPACE_DIR: $(WORKSPACE_DIR)"; exit 1;; esac
	rm -rf -- "$(WORKSPACE_DIR)"
	uv run dlthub-init "$(WORKSPACE_DIR)" $(ARGS)

WORKSPACE_INIT_DIR ?= examples/init-workspace

workspace-init: dev ## Init in place: make empty ./$(WORKSPACE_INIT_DIR), cd in, run the CLI with no positional (pass ARGS="--no-sync")
	@case "$(WORKSPACE_INIT_DIR)" in *..*|"") echo "invalid WORKSPACE_INIT_DIR: $(WORKSPACE_INIT_DIR)"; exit 1;; esac
	rm -rf -- "$(WORKSPACE_INIT_DIR)"
	mkdir -p -- "$(WORKSPACE_INIT_DIR)"
	cd "$(WORKSPACE_INIT_DIR)" && "$(CURDIR)/.venv/bin/dlthub-init" $(ARGS)

# Local/dev/stage stack testing parity with dlthub-start. dlthub-init never talks to a
# stack while scaffolding, so there are no --api-base-url flags to pass; instead we
# scaffold a fresh workspace and then pin api_base_url/auth_base_url into its
# .dlt/config.toml, which a subsequent `dlthub workspace connect` reads.
API_BASE_URL ?=
AUTH_BASE_URL ?=
DLT_RUNTIME_INSECURE ?=

workspace-env: workspace ## Scaffold ./$(WORKSPACE_DIR) then pin API_BASE_URL (+ AUTH_BASE_URL if set) into .dlt/config.toml
	@if [ -z "$(API_BASE_URL)" ]; then \
		echo "workspace-env: set API_BASE_URL (or use 'make workspace-local' / 'make workspace-dev')"; exit 1; \
	fi
	uv run python scripts/pin_workspace_urls.py "$(WORKSPACE_DIR)/.dlt/config.toml" "$(API_BASE_URL)" $(if $(AUTH_BASE_URL),"$(AUTH_BASE_URL)")
	@if [ -n "$(DLT_RUNTIME_INSECURE)" ]; then \
		echo "workspace-env: local stack uses mkcert certs — before 'dlthub workspace connect', run:"; \
		echo "    export DLT_RUNTIME_INSECURE=$(DLT_RUNTIME_INSECURE)"; \
	fi

workspace-local: ## Scaffold ./$(WORKSPACE_DIR) pointed at the local stack (api/auth.dlthub.test, insecure TLS)
	@$(MAKE) workspace-env \
		API_BASE_URL=https://api.dlthub.test \
		AUTH_BASE_URL=https://auth.dlthub.test \
		DLT_RUNTIME_INSECURE=true

workspace-dev: ## Scaffold ./$(WORKSPACE_DIR) pointed at the dev stack (api.dlthub.dev; auth shares the api host)
	@$(MAKE) workspace-env API_BASE_URL=https://api.dlthub.dev

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

scaffold-lock-upgrade: ## Re-resolve the bundled workspace uv.lock (PKG=<name> to bump one); review the diff and commit
	uv lock $(if $(PKG),--upgrade-package $(PKG),--upgrade) --project $(SCAFFOLD_DIR)

scaffold-lock-check: ## CI guard: fail if the bundled workspace uv.lock is out of sync with its pyproject
	@echo "scaffold-lock-check: checking $(SCAFFOLD_DIR)/uv.lock against its pyproject.toml…"; \
	log="$$(mktemp)"; \
	if uv lock --check --project $(SCAFFOLD_DIR) >"$$log" 2>&1; then \
		rm -f "$$log"; \
		echo "scaffold-lock-check: OK — uv.lock is in sync with pyproject.toml."; \
	else \
		echo "scaffold-lock-check: FAILED — run 'make scaffold-lock-upgrade' and commit. uv output:"; \
		cat "$$log"; rm -f "$$log"; \
		exit 1; \
	fi

#
# Skills (pulled from the dltHub AI workbench)
#

generate-skills: ## Populate skills/ from the dltHub AI workbench at the pinned WORKBENCH_REF
	uv run python scripts/generate_skills.py

update-skills: ## Bump the workbench ref (REF=<sha>, or latest) and regenerate skills/
	uv run python scripts/update_skills.py $(REF)

check-skills: ## CI guard: fail if skills/ differs from the generated output
	@echo "check-skills: regenerating skills/ (output hidden unless it fails)…"; \
	log="$$(mktemp)"; \
	if ! uv run python scripts/generate_skills.py >"$$log" 2>&1; then \
		echo "check-skills: generate-skills failed — its output:"; \
		cat "$$log"; rm -f "$$log"; exit 1; \
	fi; \
	rm -f "$$log"; \
	changed="$$(git status --porcelain -- skills)"; \
	if [ -z "$$changed" ]; then \
		echo "check-skills: OK — skills/ is up to date."; \
	else \
		echo "check-skills: FAILED — skills/ differs from 'make generate-skills'; regenerate and commit:"; \
		printf '%s\n' "$$changed" | sed 's/^/    /'; \
		git --no-pager diff -- skills; \
		exit 1; \
	fi

ci: lint-ci test test-integration lock-check scaffold-lock-check check-skills build ## Run all CI checks locally
