# Customer Service AI Coach — Makefile
#
# Minimal developer entry points. Step 1 exposes only smoke tests.
# Later steps will extend this with lint, full test suite, build, etc.

.PHONY: help test test-agent test-ui install

help:
	@echo "Targets:"
	@echo "  make install     Install agent + UI dependencies"
	@echo "  make test        Run all smoke tests (Python + TypeScript)"
	@echo "  make test-agent  Run only Python smoke tests"
	@echo "  make test-ui     Run only TS/React smoke tests"

install:
	./scripts/setup.sh

test: test-agent test-ui

test-agent:
	@echo "=== Agent (Python) smoke tests ==="
	cd agent && uv run pytest tests/ -q

test-ui:
	@echo "=== UI (TypeScript) smoke tests ==="
	npm --prefix coach-ui test -- --run
