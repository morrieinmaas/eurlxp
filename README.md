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

## Installation

```bash
# Using pip
pip install eurlxp

# Using uv
uv add eurlxp

# With SPARQL support
pip install eurlxp[sparql]
```

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
from eurlxp import get_html_by_celex_id, parse_html

# Fetch and parse a regulation
celex_id = "32019R0947"
html = get_html_by_celex_id(celex_id)
df = parse_html(html)

# Get Article 1
df_article_1 = df[df.article == "1"]
print(df_article_1.iloc[0].text)
# "This Regulation lays down detailed provisions for the operation of unmanned aircraft systems..."
```

### Async Usage

```python
import asyncio
from eurlxp import AsyncEURLexClient, parse_html

async def fetch_documents():
    async with AsyncEURLexClient() as client:
        # Fetch multiple documents concurrently
        docs = await client.fetch_multiple(["32019R0947", "32019R0945"])
        for celex_id, html in docs.items():
            df = parse_html(html)
            print(f"{celex_id}: {len(df)} rows")

asyncio.run(fetch_documents())
```

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
| `EURLexClient` | Synchronous HTTP client |
| `AsyncEURLexClient` | Asynchronous HTTP client |

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