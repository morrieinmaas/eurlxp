# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2025-01-08

### Fixed

- CLI now shows help by default when no command is provided

## [0.2.1] - 2025-01-08

### Changed

- Publish workflow now requires CI to pass before publishing
- Publish workflow checks CHANGELOG for version entry before publishing

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

[Unreleased]: https://github.com/morrieinmaas/eurlxp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/morrieinmaas/eurlxp/releases/tag/v0.1.0
