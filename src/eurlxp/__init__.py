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
    AsyncEURLexClient,
    EURLexClient,
    get_html_by_celex_id,
    get_html_by_cellar_id,
    prepend_prefixes,
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
    parse_article_paragraphs,
    parse_html,
    process_paragraphs,
)
from eurlxp.sparql import (
    convert_sparql_output_to_dataframe,
    get_celex_dataframe,
    get_documents,
    get_regulations,
    guess_celex_ids_via_eurlex,
    run_query,
)

__version__ = version("eurlxp")
__all__ = [
    # Version
    "__version__",
    # Client
    "EURLexClient",
    "AsyncEURLexClient",
    "get_html_by_celex_id",
    "get_html_by_cellar_id",
    "prepend_prefixes",
    "simplify_iri",
    # Parser
    "parse_html",
    "parse_article_paragraphs",
    "get_celex_id",
    "get_possible_celex_ids",
    "process_paragraphs",
    # SPARQL
    "run_query",
    "convert_sparql_output_to_dataframe",
    "get_celex_dataframe",
    "guess_celex_ids_via_eurlex",
    "get_regulations",
    "get_documents",
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
