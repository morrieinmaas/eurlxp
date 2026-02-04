# eurlxp - justfile
# Run `just` or `just help` to see available commands

# Default recipe - show help
default:
    @just --list

# Install dependencies
install:
    uv sync

# Install with dev dependencies
dev:
    uv sync --all-extras

# Run linting (ruff check)
lint:
    uv run ruff check src tests

# Format code (ruff format)
format:
    uv run ruff format src tests
    uv run ruff check --fix src tests

# Run all checks (lint + type check)
check:
    uv run ruff check src tests
    uv run ruff format --check src tests
    uv run pyright

# Run all tests
test:
    uv sync --all-extras
    uv run pytest -v

# Run integration tests
test-integration:
    uv sync --all-extras
    uv run pytest -v -m integration

# Run unit tests only (excluding integration)
test-unit:
    uv sync --all-extras
    uv run pytest -v -m "not integration"

# Run live tests against real EUR-Lex endpoints with all ID formats
test-live:
    uv sync --all-extras
    uv run python scripts/test_live_fetch.py

# Test WAF detection and SPARQL fallback (real network requests)
test-waf:
    uv sync --all-extras
    uv run python scripts/test_waf_fallback.py

# Test EUR-Lex endpoints with curl (detects WAF challenge)
test-curl:
    #!/usr/bin/env bash
    echo "EUR-Lex Endpoint Status Check"
    echo "=============================="
    echo ""
    echo "1. HTML Endpoint (CELEX:32019R0947):"
    response=$(curl -s -H "User-Agent: Mozilla/5.0" "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0947")
    if echo "$response" | grep -q "awswaf.com\|AwsWafIntegration\|challenge.js"; then
        echo "   ❌ WAF CHALLENGE DETECTED - Bot detection is blocking requests"
        echo "   → SPARQL fallback will be used automatically"
    else
        size=$(echo "$response" | wc -c | tr -d ' ')
        echo "   ✅ OK - Direct HTML access working ($size bytes)"
    fi
    echo ""
    echo "2. SPARQL Endpoint:"
    status=$(curl -s -o /dev/null -w "%{http_code}" "https://publications.europa.eu/webapi/rdf/sparql?query=SELECT%20%3Fs%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%201")
    if [ "$status" = "200" ]; then
        echo "   ✅ OK - SPARQL endpoint available (HTTP $status)"
    elif [ "$status" = "503" ]; then
        echo "   ⚠️  TEMPORARILY UNAVAILABLE (HTTP 503) - Will retry with backoff"
    else
        echo "   ❌ ERROR (HTTP $status)"
    fi
    echo ""

# Build the package
build:
    uv build

# Publish to PyPI (requires PYPI_TOKEN env var)
publish:
    #!/usr/bin/env bash
    if [ -z "$PYPI_TOKEN" ]; then
        echo "Error: PYPI_TOKEN environment variable is not set"
        exit 1
    fi
    uv publish --token $PYPI_TOKEN

# Publish to TestPyPI (requires TEST_PYPI_TOKEN env var)
publish-test:
    #!/usr/bin/env bash
    if [ -z "$TEST_PYPI_TOKEN" ]; then
        echo "Error: TEST_PYPI_TOKEN environment variable is not set"
        exit 1
    fi
    uv publish --publish-url https://test.pypi.org/legacy/ --token $TEST_PYPI_TOKEN

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/ .coverage coverage.xml htmlcov/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
