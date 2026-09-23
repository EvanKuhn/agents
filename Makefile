.PHONY: help format lint types
.DEFAULT_GOAL := help

# Print usage, built from the "## description" comment on each target
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  %-8s %s\n", $$1, $$2}'

# Import sorting is a lint rule in ruff, so the formatter alone doesn't do it
format: ## Sort imports, then reformat code (ruff)
	uv run ruff check --select I --fix
	uv run ruff format

lint: ## Check for lint errors (ruff)
	uv run ruff check

types: ## Type check (ty)
	uv run ty check
