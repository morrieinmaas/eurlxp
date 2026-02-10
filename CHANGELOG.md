# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-02-10

### Fixed

- **`parse_html` metadata propagation** - Fixed bug where `article`, `group`, and `section` columns were assigned the same values (from the last element in the document) for all rows. The parser now processes `<p>` tags in a single pass in document order, so each row reflects its actual structural position. Preamble/recital rows before any article now correctly have `None` for `article`. ([#1](https://github.com/morrieinmaas/eurlxp/issues/1))

## [0.4.0] - 2026-02-04

### Added

- **Date-based document querying** - New `get_ids_and_urls_via_date()` function to query documents by date range via SPARQL
  - Returns `DocumentReference` objects with both CELEX ID and cellar URL
  - Cellar URL always works for fetching, even when CELEX ID is non-standard
  - `date_type` parameter to query by publication date, modification date, or creation date
  - Use `DateType.MODIFIED` to find amended documents regardless of original publication year
- **CELEX ID validation** - New functions to parse and validate CELEX IDs:
  - `parse_celex_id()` - Parse CELEX ID into components (sector, year, doc_type, number, suffix)
  - `is_valid_celex_id()` - Check if a string is a valid CELEX ID format
  - Correctly identifies OJ references (like `C/2026/00064`) as non-CELEX formats
- **Cellar URL fetching** - New `get_html_by_cellar_url()` function to fetch documents directly by cellar URL
  - Sync method on `EURLexClient`
  - Async method on `AsyncEURLexClient`
  - Convenience function at module level
  - Handles URLs with suffixes like `/DOC_1`
- **DateType enum** - For specifying which date field to filter on:
  - `DateType.DOCUMENT` - Publication date (default)
  - `DateType.MODIFIED` - Last modification date (for finding updates to old documents)
  - `DateType.CREATED` - Creation date in CELLAR
- **DocumentReference dataclass** - Structured return type for document queries containing:
  - `cellar_url` - Always available, always works for fetching
  - `celex_id` - Valid CELEX ID or None if format is non-standard
  - `raw_id` - Original ID from query (may be OJ reference or have revision suffix)
  - `document_date` - The date matching the query filter
- **Unified document fetching** - New functions that auto-detect identifier types:
  - `get_html()` - Fetch a single document by any identifier type (including OJ references via SPARQL lookup)
  - `fetch_documents()` - Batch fetch multiple documents with mixed identifier types
  - `detect_id_type()` - Detect whether an identifier is CELEX, cellar URL, cellar ID, or OJ reference
  - `lookup_cellar_url()` - Look up cellar URL for any identifier via SPARQL (used internally by `get_html()`)
- **OJ reference detection** - `detect_id_type()` now returns `"oj_reference"` for Official Journal references like `C/2026/00064`
- **HTTP retry with exponential backoff** - All HTTP requests now automatically retry on transient server errors (500, 502, 503, 504)
  - `ClientConfig` now supports `max_retries`, `retry_delay`, and `retry_backoff` parameters
  - SPARQL fallback and PDF extraction also benefit from retry logic
  - Default: 3 retries with 2s initial delay and 2x backoff (2s → 4s → 8s)

### Fixed

- Fixed broken import in `guess_celex_ids_via_eurlex()` (`from parser` → `from eurlxp.parser`)
- Fixed `get_html_by_cellar_url` convenience function signature (removed erroneous `self` parameter)
- Added missing rate limiting to sync `get_html_by_cellar_url` method
- Fixed docstring typos in cellar URL methods

## [0.3.3] - 2025-01-14

### Added

- **PDF extraction fallback** - When XHTML is not available (older documents from 1983 and earlier), automatically extracts text from PDF using PyMuPDF
- **PyMuPDF as core dependency** - PDF extraction is now always available

### Fixed

- **Consistent DataFrame columns** - `parse_html()` now always returns 8 columns (`text`, `type`, `ref`, `document`, `article`, `paragraph`, `group`, `section`) instead of variable column count
- **Fallback for unknown formats** - Extracts text from all `<p>` tags when no known CSS classes are found
- **HTML parser fallback** - Tries lxml HTML parser when lxml-xml (XHTML) parser finds no content, fixing parsing of older HTML documents
- **Old documents now parseable** - Documents that only have PDF versions can now be fetched and parsed

## [0.3.2] - 2025-01-14

### Fixed

- **Parser now handles Commission proposal format** - Added support for CSS classes used in Commission documents (`Normal`, `Titreobjet`, `Titrearticle`, `Typedudocument`)
- **Switched to BeautifulSoup-only parsing** for consistent handling of all EUR-Lex document formats (OJ, Commission proposals, etc.) - fixes issue where some documents parsed as empty DataFrames

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
