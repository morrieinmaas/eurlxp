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

test-curl:  ## Test EUR-Lex endpoints with curl (shows WAF challenge if blocked)
	@echo "Testing EUR-Lex HTML endpoint..."
	@echo "================================"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\nContent-Type: %{content_type}\nSize: %{size_download} bytes\n" \
		-H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
		"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0947"
	@echo ""
	@echo "Checking for WAF challenge in response..."
	@curl -s -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
		"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0947" | head -20
	@echo ""
	@echo "================================"
	@echo "Testing SPARQL endpoint..."
	@echo "================================"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
		"https://publications.europa.eu/webapi/rdf/sparql?query=SELECT%20%3Fs%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%201"

clean:  ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage coverage.xml htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
