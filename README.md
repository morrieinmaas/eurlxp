# eurlxp

<p>
    <a href="https://github.com/morrieinmaas/eurlxp/actions/workflows/ci.yml"><img src="https://github.com/morrieinmaas/eurlxp/actions/workflows/ci.yml/badge.svg" alt="CI" height="18"></a>
    <a href="https://badge.fury.io/py/eurlxp"><img src="https://badge.fury.io/py/eurlxp.svg" alt="PyPI version" height="18"></a>
    <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" height="18"></a>
    <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python versions" height="18">
</p>

A modern EUR-Lex parser for Python. Fetch and parse EU legal documents with async support, type hints, and a CLI.

> **Note**: This is a modern rewrite inspired by [kevin91nl/eurlex](https://github.com/kevin91nl/eurlex), built with UV, httpx, Pydantic, and Typer.

## Features

- **Modern Python** - Supports Python 3.10-3.14
- **Async support** - Fetch multiple documents concurrently
- **Type hints** - Full type annotations for IDE support
- **CLI** - Command-line interface with Typer
- **Pydantic models** - Validated, structured data
- **Drop-in compatible** - Same API as the original eurlex package
- **Bot detection handling** - Browser-like headers and WAF challenge detection
- **Rate limiting** - Configurable delays between requests
- **SPARQL support** - Alternative data source that bypasses HTML scraping

## Installation

```bash
# Using pip
pip install eurlxp

# Using uv
uv add eurlxp

# With SPARQL support (required for get_celex_dataframe, run_query, get_regulations, etc.)
pip install eurlxp[sparql]
# or
uv add eurlxp[sparql]
```

> **Note**: SPARQL functions (`get_celex_dataframe`, `run_query`, `get_regulations`, `get_documents`, `guess_celex_ids_via_eurlex`) require the optional `sparql` dependencies. If you see `ImportError: SPARQL dependencies not installed`, install with `pip install eurlxp[sparql]`.

## How It Works

This package fetches EU legal documents from EUR-Lex using their public HTML endpoints:

```text
https://eur-lex.europa.eu/legal-content/{LANG}/TXT/HTML/?uri=CELEX:{CELEX_ID}
```

You can verify this manually with curl:

```bash
# Fetch a regulation (EU Drone Regulation 2019/947)
curl -s "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0947" | head -50

# Or with a different language (German)
curl -s "https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32019R0947" | head -50
```

The equivalent using this package's CLI:

```bash
# Fetch as HTML
uvx eurlxp fetch 32019R0947 --format html | head -50

# Fetch and parse to JSON
uvx eurlxp fetch 32019R0947 --format json | head -30

# Fetch and parse to CSV
uvx eurlxp fetch 32019R0947 --format csv | head -10

# Get document info (shows row count, articles, etc.)
uvx eurlxp info 32019R0947
```

## Quick Start

```python
from eurlxp import get_html_by_celex_id, parse_html, WAFChallengeError

# Fetch and parse a regulation
celex_id = "32019R0947"
try:
    html = get_html_by_celex_id(celex_id)
    df = parse_html(html)

    # Get Article 1
    df_article_1 = df[df.article == "1"]
    print(df_article_1.iloc[0].text)
    # "This Regulation lays down detailed provisions for the operation of unmanned aircraft systems..."
except WAFChallengeError:
    print("Bot detection triggered - try using SPARQL functions instead")
```

### Async Usage

```python
import asyncio
from eurlxp import AsyncEURLexClient, parse_html

async def fetch_documents():
    # Use rate limiting to avoid bot detection
    async with AsyncEURLexClient(request_delay=2.0) as client:
        # Fetch multiple documents concurrently
        docs = await client.fetch_multiple(["32019R0947", "32019R0945"])
        for celex_id, html in docs.items():
            df = parse_html(html)
            print(f"{celex_id}: {len(df)} rows")

asyncio.run(fetch_documents())
```

### Handling Bot Detection

EUR-Lex uses AWS WAF (Web Application Firewall) with JavaScript challenges to detect automated requests. **This cannot be bypassed in pure Python** because it requires JavaScript execution to solve a cryptographic puzzle. The library provides several strategies:

```python
from eurlxp import EURLexClient, ClientConfig, WAFChallengeError

# Strategy 1: Automatic SPARQL fallback (recommended)
# When WAF blocks HTML scraping, automatically fetch metadata via SPARQL
config = ClientConfig(sparql_fallback=True)
with EURLexClient(config=config) as client:
    html = client.get_html_by_celex_id("32019R0947")  # Falls back to SPARQL if blocked

# Strategy 2: Use rate limiting to avoid triggering WAF
with EURLexClient(request_delay=2.0) as client:  # 2 second delay between requests
    html = client.get_html_by_celex_id("32019R0947")

# Strategy 3: Use custom configuration
config = ClientConfig(
    request_delay=3.0,           # Delay between requests
    use_browser_headers=True,    # Use browser-like headers (default)
    referer="https://eur-lex.europa.eu/",  # Add referer header
)
with EURLexClient(config=config) as client:
    html = client.get_html_by_celex_id("32019R0947")

# Strategy 4: Handle WAF challenges manually
try:
    html = get_html_by_celex_id("32019R0947")
except WAFChallengeError:
    # Fall back to SPARQL manually
    from eurlxp import get_documents
    docs = get_documents(types=["REG"], limit=10)

# Strategy 5: Disable WAF exception (get raw challenge HTML)
config = ClientConfig(raise_on_waf=False)
with EURLexClient(config=config) as client:
    html = client.get_html_by_celex_id("32019R0947")  # Returns challenge HTML if blocked
```

> **Why can't we bypass WAF in Python?** AWS WAF requires a real browser to execute JavaScript that solves a cryptographic challenge and sets a cookie. HTTP libraries like httpx can't execute JavaScript. For browser automation, consider Playwright or Selenium, but SPARQL is the cleaner solution.

### Using SPARQL (Recommended for Bulk Data)

The SPARQL endpoint (`https://publications.europa.eu/webapi/rdf/sparql`) doesn't trigger bot detection and is ideal for bulk operations. It's the **recommended approach** when HTML scraping is blocked.

```python
from eurlxp import get_documents, get_regulations, run_query, guess_celex_ids_via_eurlex

# Convert slash notation to CELEX ID (uses SPARQL, not HTML scraping)
celex_ids = guess_celex_ids_via_eurlex("2019/947")
# Returns: ['32019R0947']

# Get list of regulations (returns CELLAR IDs)
cellar_ids = get_regulations(limit=100)

# Get documents with metadata
docs = get_documents(types=["REG", "DIR"], limit=50)
for doc in docs:
    print(f"{doc['celex']}: {doc['date']} - {doc['type']}")

# Run custom SPARQL queries
results = run_query("""
    SELECT ?doc ?celex WHERE {
        ?doc cdm:resource_legal_id_celex ?celex .
    } LIMIT 10
""")
```

**SPARQL functions include automatic retry with exponential backoff** for handling temporary 503 errors:

```python
from eurlxp import run_query, SPARQLServiceError

try:
    # Automatic retry: 3 attempts with 2s, 4s, 8s delays
    results = run_query(query)
    
    # Or customize retry behavior
    results = run_query(query, max_retries=5, retry_delay=3.0)
except SPARQLServiceError as e:
    print(f"SPARQL endpoint unavailable: {e}")
```

> **Note**: SPARQL functions require `pip install eurlxp[sparql]`

### CLI Usage

```bash
# Fetch a document
eurlxp fetch 32019R0947 -o regulation.html

# Parse and convert to CSV
eurlxp fetch 32019R0947 -f csv -o regulation.csv

# Get document info
eurlxp info 32019R0947

# Convert slash notation to CELEX ID
eurlxp celex 2019/947
# Output: 32019R0947
```

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `get_html_by_celex_id(celex_id, language="en")` | Fetch HTML by CELEX ID |
| `get_html_by_cellar_id(cellar_id, language="en")` | Fetch HTML by CELLAR ID |
| `parse_html(html)` | Parse HTML to DataFrame |
| `get_celex_id(slash_notation, document_type="R", sector_id="3")` | Convert slash notation to CELEX ID |
| `get_possible_celex_ids(slash_notation)` | Get all possible CELEX IDs |

### Classes

| Class | Description |
|-------|-------------|
| `EURLexClient` | Synchronous HTTP client with rate limiting and WAF detection |
| `AsyncEURLexClient` | Asynchronous HTTP client with rate limiting and WAF detection |
| `ClientConfig` | Configuration dataclass for client behavior |
| `WAFChallengeError` | Exception raised when bot detection is triggered |

### ClientConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | float | 30.0 | Request timeout in seconds |
| `headers` | dict | None | Custom headers to merge with defaults |
| `request_delay` | float | 0.0 | Delay between requests (rate limiting) |
| `use_browser_headers` | bool | True | Use browser-like headers to avoid detection |
| `referer` | str | None | Optional referer header |
| `raise_on_waf` | bool | True | Raise exception on WAF challenge |
| `sparql_fallback` | bool | True | Auto-fallback to SPARQL when WAF blocks requests |

### DataFrame Columns

| Column | Description |
|--------|-------------|
| `text` | The text content |
| `type` | Content type (text, link, etc.) |
| `document` | Document title |
| `article` | Article number |
| `article_subtitle` | Article subtitle |
| `paragraph` | Paragraph number |
| `group` | Group heading |
| `section` | Section heading |
| `ref` | Reference path (e.g., `["(1)", "(a)"]`) |

## Development

```bash
# Clone the repository
git clone https://github.com/morrieinmaas/eurlxp.git
cd eurlxp

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
uv run ruff format src tests

# Type checking
uv run pyright
```

## Publishing to PyPI

```bash
# Build the package
uv build

# Publish to PyPI (requires PYPI_TOKEN)
uv publish --token $PYPI_TOKEN
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Inspired by [kevin91nl/eurlex](https://github.com/kevin91nl/eurlex).