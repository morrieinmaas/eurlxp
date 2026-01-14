# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2025-01-14

### Fixed

- **SPARQL fallback now fetches actual document content** via RDF graph traversal (Work → Expression → Manifestation → XHTML) instead of returning placeholder HTML

## [0.3.0] - 2025-01-14

### Added

- **Bot detection handling**: `WAFChallengeError` exception when EUR-Lex returns AWS WAF JavaScript challenges
- **SPARQL fallback**: `sparql_fallback` option to automatically fall back to SPARQL when WAF blocks HTML scraping
- **Rate limiting**: `request_delay` parameter for clients to add delays between requests
- **Client configuration**: `ClientConfig` dataclass for configuring client behavior
  - `timeout` - Request timeout in seconds
  - `headers` - Custom headers to merge with defaults
  - `request_delay` - Delay between requests for rate limiting
  - `use_browser_headers` - Toggle browser-like vs minimal headers
  - `referer` - Optional referer header
  - `raise_on_waf` - Whether to raise exception on WAF challenge
  - `sparql_fallback` - Automatically fallback to SPARQL on WAF challenge (default: True)
- **Global config**: `get_default_config()` and `set_default_config()` functions
- **SPARQL retry logic**: Automatic retry with exponential backoff for 503 errors
- **SPARQL exception**: `SPARQLServiceError` for handling SPARQL endpoint failures
- Browser-like default headers to reduce bot detection triggers

### Changed

- `EURLexClient` and `AsyncEURLexClient` now accept `config` parameter for full configuration
- `run_query()` now accepts `max_retries`, `retry_delay`, and `retry_backoff` parameters
- Default headers now mimic Chrome browser to avoid AWS WAF detection
- Improved README with bot detection strategies and SPARQL usage examples

### Fixed

- Better error messages when bot detection is triggered
- SPARQL queries now retry automatically on temporary 503 errors

## [0.2.5] - 2025-01-08

### Changed

- Improved README documentation about SPARQL optional dependencies

## [0.2.4] - 2025-01-08

### Changed

- Use HTTPS for SPARQL endpoint
- Add documentation comments clarifying SPARQL endpoint is still official
- Add curl and CLI examples to README

## [0.2.3] - 2025-01-08

### Fixed

- Update EUR-Lex API endpoints to use new eur-lex.europa.eu URLs (old publications.europa.eu/resource/ endpoints return 400 errors)
- Add support for new EUR-Lex HTML format with `oj-` prefixed CSS classes
- Use lxml-xml parser for proper XHTML parsing (BeautifulSoup fallback)
- CLI now shows help by default when no command is provided

### Changed

- Publish workflow now requires CI to pass before publishing
- Publish workflow checks CHANGELOG for version entry before publishing
- Version is now dynamically read from package metadata

## [0.2.0] - 2025-01-08

### Added

- `run_query()` - Execute SPARQL queries on EUR-Lex
- `convert_sparql_output_to_dataframe()` - Convert SPARQL results to DataFrame
- `get_celex_dataframe()` - Get CELEX data as RDF graph DataFrame
- `guess_celex_ids_via_eurlex()` - Lookup CELEX IDs via EUR-Lex SPARQL
- `get_regulations()` - Retrieve list of regulation CELLAR IDs
- `get_documents()` - Retrieve documents by type with metadata
- Full API parity with original eurlex package

### Changed

- SPARQL functions require optional `eurlxp[sparql]` dependencies

## [0.1.0] - 2025-01-08

### Added

- Initial release
- `get_html_by_celex_id()` - Fetch EUR-Lex documents by CELEX ID
- `get_html_by_cellar_id()` - Fetch EUR-Lex documents by CELLAR ID
- `parse_html()` - Parse EUR-Lex HTML to pandas DataFrame
- `get_celex_id()` - Convert slash notation to CELEX ID
- `get_possible_celex_ids()` - Get all possible CELEX IDs for a slash notation
- `EURLexClient` - Synchronous HTTP client
- `AsyncEURLexClient` - Asynchronous HTTP client with concurrent fetching
- CLI with `fetch`, `parse`, `info`, `celex`, and `version` commands
- Full type hints and Pydantic models
- Support for Python 3.10-3.14

[0.2.3]: https://github.com/morrieinmaas/eurlxp/compare/v0.2.0...v0.2.3
[0.2.0]: https://github.com/morrieinmaas/eurlxp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/morrieinmaas/eurlxp/releases/tag/v0.1.0
