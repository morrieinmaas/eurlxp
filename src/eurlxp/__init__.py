"""eurlxp - A modern EUR-Lex parser for Python.

Fetch and parse EU legal documents from EUR-Lex.

Examples
--------
>>> from eurlxp import get_html_by_celex_id, parse_html
>>> html = get_html_by_celex_id("32019R0947")
>>> df = parse_html(html)
>>> len(df) > 0
True
"""

from importlib.metadata import version

from eurlxp.client import (
    DEFAULT_HEADERS,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT,
    MINIMAL_HEADERS,
    AsyncEURLexClient,
    ClientConfig,
    EURLexClient,
    WAFChallengeError,
    detect_id_type,
    fetch_documents,
    get_default_config,
    get_html,
    get_html_by_celex_id,
    get_html_by_cellar_id,
    get_html_by_cellar_url,
    prepend_prefixes,
    set_default_config,
    simplify_iri,
)
from eurlxp.models import (
    EURLEX_PREFIXES,
    DocumentInfo,
    DocumentMetadata,
    DocumentType,
    ParseContext,
    ParsedItem,
    ParseResult,
    SectorId,
)
from eurlxp.parser import (
    get_celex_id,
    get_possible_celex_ids,
    is_valid_celex_id,
    parse_article_paragraphs,
    parse_celex_id,
    parse_html,
    process_paragraphs,
)
from eurlxp.sparql import (
    DateType,
    DocumentReference,
    SPARQLServiceError,
    convert_sparql_output_to_dataframe,
    get_celex_dataframe,
    get_documents,
    get_ids_and_urls_via_date,
    get_regulations,
    guess_celex_ids_via_eurlex,
    lookup_cellar_url,
    run_query,
)

__version__ = version("eurlxp")
__all__ = [
    # Version
    "__version__",
    # Client
    "EURLexClient",
    "AsyncEURLexClient",
    "ClientConfig",
    "get_default_config",
    "set_default_config",
    "get_html",
    "get_html_by_celex_id",
    "get_html_by_cellar_id",
    "get_html_by_cellar_url",
    "fetch_documents",
    "detect_id_type",
    "prepend_prefixes",
    "simplify_iri",
    "DEFAULT_HEADERS",
    "MINIMAL_HEADERS",
    "DEFAULT_TIMEOUT",
    "DEFAULT_REQUEST_DELAY",
    "WAFChallengeError",
    # Parser
    "parse_html",
    "parse_article_paragraphs",
    "get_celex_id",
    "get_possible_celex_ids",
    "parse_celex_id",
    "is_valid_celex_id",
    "process_paragraphs",
    # SPARQL
    "run_query",
    "convert_sparql_output_to_dataframe",
    "get_celex_dataframe",
    "guess_celex_ids_via_eurlex",
    "get_regulations",
    "get_documents",
    "get_ids_and_urls_via_date",
    "lookup_cellar_url",
    "DocumentReference",
    "DateType",
    "SPARQLServiceError",
    # Models
    "DocumentType",
    "SectorId",
    "ParsedItem",
    "DocumentMetadata",
    "DocumentInfo",
    "ParseContext",
    "ParseResult",
    "EURLEX_PREFIXES",
]
