.DEFAULT_GOAL := help

.PHONY: help dev lint lint-fix format format-check fl lint-ci test test-integration build clean-dist publish ci lock-upgrade lock-check scaffold-lock-upgrade scaffold-lock-check workspace workspace-init

PYTHON_SOURCES := src tests tests_integration
SCAFFOLD_DIR ?= src/dlthub_init/scaffolds/minimal_workspace

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

build: dev ## Build the package wheel
	uv build

clean-dist: ## Remove dist/ directory
	-@rm -r dist/

publish: clean-dist build ## Build and publish dlthub-init to PyPI
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

ci: lint-ci test test-integration lock-check scaffold-lock-check build ## Run all CI checks locally
