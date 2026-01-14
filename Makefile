.PHONY: help install dev lint format check test test-integration test-all test-waf test-curl build publish publish-test clean

PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff
PYRIGHT := uv run pyright

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

dev:  ## Install with dev dependencies
	uv sync --all-extras

lint:  ## Run linting (ruff check)
	$(RUFF) check src tests

format:  ## Format code (ruff format)
	$(RUFF) format src tests
	$(RUFF) check --fix src tests

check:  ## Run all checks (lint + type check)
	$(RUFF) check src tests
	$(RUFF) format --check src tests
	$(PYRIGHT)

test:  ## Run tests (excluding integration)
	uv sync --all-extras
	$(PYTEST) -v -m "not integration"

test-integration:  ## Run integration tests
	uv sync --all-extras
	$(PYTEST) -v -m integration

test-all:  ## Run all tests
	uv sync --all-extras
	$(PYTEST) -v

build:  ## Build the package
	uv build

publish:  ## Publish to PyPI (requires PYPI_TOKEN env var)
	@if [ -z "$$PYPI_TOKEN" ]; then \
		echo "Error: PYPI_TOKEN environment variable is not set"; \
		exit 1; \
	fi
	uv publish --token $$PYPI_TOKEN

publish-test:  ## Publish to TestPyPI (requires TEST_PYPI_TOKEN env var)
	@if [ -z "$$TEST_PYPI_TOKEN" ]; then \
		echo "Error: TEST_PYPI_TOKEN environment variable is not set"; \
		exit 1; \
	fi
	uv publish --publish-url https://test.pypi.org/legacy/ --token $$TEST_PYPI_TOKEN

test-waf:  ## Test WAF detection and SPARQL fallback (real network requests)
	uv sync --all-extras
	$(PYTHON) scripts/test_waf_fallback.py

test-curl:  ## Test EUR-Lex endpoints with curl (detects WAF challenge)
	@echo "EUR-Lex Endpoint Status Check"
	@echo "=============================="
	@echo ""
	@echo "1. HTML Endpoint (CELEX:32019R0947):"
	@response=$$(curl -s -H "User-Agent: Mozilla/5.0" "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0947"); \
	if echo "$$response" | grep -q "awswaf.com\|AwsWafIntegration\|challenge.js"; then \
		echo "   ❌ WAF CHALLENGE DETECTED - Bot detection is blocking requests"; \
		echo "   → SPARQL fallback will be used automatically"; \
	else \
		size=$$(echo "$$response" | wc -c | tr -d ' '); \
		echo "   ✅ OK - Direct HTML access working ($$size bytes)"; \
	fi
	@echo ""
	@echo "2. SPARQL Endpoint:"
	@status=$$(curl -s -o /dev/null -w "%{http_code}" "https://publications.europa.eu/webapi/rdf/sparql?query=SELECT%20%3Fs%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%201"); \
	if [ "$$status" = "200" ]; then \
		echo "   ✅ OK - SPARQL endpoint available (HTTP $$status)"; \
	elif [ "$$status" = "503" ]; then \
		echo "   ⚠️  TEMPORARILY UNAVAILABLE (HTTP 503) - Will retry with backoff"; \
	else \
		echo "   ❌ ERROR (HTTP $$status)"; \
	fi
	@echo ""

clean:  ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage coverage.xml htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
