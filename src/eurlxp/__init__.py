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

from eurlxp.client import (
    AsyncEURLexClient,
    EURLexClient,
    get_html_by_celex_id,
    get_html_by_cellar_id,
    prepend_prefixes,
    simplify_iri,
)
from eurlxp.models import (
    DocumentInfo,
    DocumentMetadata,
    DocumentType,
    EURLEX_PREFIXES,
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

__version__ = "0.1.0"
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
