"""SPARQL query functions for EUR-Lex.

This module requires the optional `sparql` dependencies:
    pip install eurlxp[sparql]

The SPARQL endpoint (https://publications.europa.eu/webapi/rdf/sparql) is the recommended
way to query EUR-Lex data as it doesn't trigger bot detection like HTML scraping does.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import pandas as pd

from eurlxp.client import prepend_prefixes

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DateType(str, Enum):
    """Date field to use when querying documents.

    Attributes
    ----------
    DOCUMENT : str
        The document publication date (cdm:work_date_document).
        Use this for the original publication date of the document.
    CREATED : str
        The creation date in CELLAR (cdm:work_date_creation).
    MODIFIED : str
        The last modification date (cdm:work_date_lastUpdate).
        Use this to find documents that have been updated/amended.
    """

    DOCUMENT = "document"
    CREATED = "created"
    MODIFIED = "modified"


# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier


class SPARQLServiceError(Exception):
    """Raised when the SPARQL endpoint returns a service error (e.g., 503).

    This typically indicates the server is temporarily overloaded.
    The library will automatically retry with exponential backoff.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _check_sparql_dependencies() -> None:
    """Check if SPARQL dependencies are installed."""
    try:
        import rdflib  # noqa: F401
        from SPARQLWrapper import SPARQLWrapper  # noqa: F401
    except ImportError as e:
        raise ImportError("SPARQL dependencies not installed. Install with: pip install eurlxp[sparql]") from e


def run_query(
    query: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF,
) -> dict:
    """Run a SPARQL query on EUR-Lex with automatic retry on failure.

    Parameters
    ----------
    query : str
        The SPARQL query to run.
    max_retries : int
        Maximum number of retry attempts (default: 3).
    retry_delay : float
        Initial delay between retries in seconds (default: 2.0).
    retry_backoff : float
        Exponential backoff multiplier (default: 2.0).

    Returns
    -------
    dict
        A dictionary containing the results.

    Raises
    ------
    SPARQLServiceError
        If the query fails after all retries.

    Examples
    --------
    >>> results = run_query("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")  # doctest: +SKIP
    >>> results = run_query(query, max_retries=5, retry_delay=3.0)  # More retries
    """
    _check_sparql_dependencies()
    from urllib.error import HTTPError

    from SPARQLWrapper import JSON, SPARQLWrapper
    from SPARQLWrapper.SPARQLExceptions import EndPointInternalError, EndPointNotFound, QueryBadFormed

    sparql = SPARQLWrapper("https://publications.europa.eu/webapi/rdf/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    last_error: Exception | None = None
    current_delay = retry_delay

    for attempt in range(max_retries + 1):
        try:
            results = sparql.query().convert()
            return dict(results)  # type: ignore[arg-type]
        except (HTTPError, EndPointInternalError) as e:
            last_error = e
            status_code = getattr(e, "code", None) or getattr(e, "status_code", None)

            if attempt < max_retries:
                logger.warning(
                    "SPARQL query failed (attempt %d/%d, status=%s): %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries + 1,
                    status_code,
                    str(e)[:100],
                    current_delay,
                )
                time.sleep(current_delay)
                current_delay *= retry_backoff
            else:
                logger.error("SPARQL query failed after %d attempts: %s", max_retries + 1, e)
        except (QueryBadFormed, EndPointNotFound) as e:
            raise SPARQLServiceError(f"SPARQL query error: {e}") from e

    raise SPARQLServiceError(
        f"SPARQL endpoint unavailable after {max_retries + 1} attempts. Last error: {last_error}",
        status_code=getattr(last_error, "code", None),
    )


def convert_sparql_output_to_dataframe(sparql_results: dict) -> pd.DataFrame:
    """Convert SPARQL output to a DataFrame.

    Parameters
    ----------
    sparql_results : dict
        A dictionary containing the SPARQL results.

    Returns
    -------
    pd.DataFrame
        The DataFrame representation of the SPARQL results.

    Examples
    --------
    >>> convert_sparql_output_to_dataframe({'results': {'bindings': [{'subject': {'value': 'cdm:test'}}]}}).to_dict()
    {'subject': {0: 'cdm:test'}}
    """
    from eurlxp.client import simplify_iri

    items = [{key: simplify_iri(item[key]["value"]) for key in item} for item in sparql_results["results"]["bindings"]]
    return pd.DataFrame(items)


def get_celex_dataframe(celex_id: str) -> pd.DataFrame:
    """Get CELEX data delivered in a DataFrame.

    Parameters
    ----------
    celex_id : str
        The CELEX ID to get the data for.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the results with columns 's', 'o', 'p'.
    """
    _check_sparql_dependencies()
    import rdflib

    from eurlxp.client import simplify_iri

    graph = rdflib.Graph()
    graph.parse(f"http://publications.europa.eu/resource/celex/{celex_id}?language=eng")

    items = [{key: simplify_iri(str(item[key])) for key in range(len(item))} for item in graph]
    df = pd.DataFrame(items)
    if len(df.columns) >= 3:
        df.columns = ["s", "o", "p"]  # type: ignore[assignment]
    return df


def guess_celex_ids_via_eurlex(
    slash_notation: str,
    document_type: str | None = None,
    sector_id: str | None = None,
) -> list[str]:
    """Guess CELEX IDs for a slash notation by looking it up via EUR-Lex.

    Parameters
    ----------
    slash_notation : str
        The slash notation of the document (like 2019/947).
    document_type : str, optional
        The type of the document (e.g. "R" for regulations).
    sector_id : str, optional
        The sector ID (e.g. "3").

    Returns
    -------
    list[str]
        A list of possible CELEX IDs.

    Examples
    --------
    >>> celex_ids = guess_celex_ids_via_eurlex("2019/947")  # doctest: +SKIP
    """
    from eurlxp.client import prepend_prefixes
    from eurlxp.parser import get_possible_celex_ids

    slash_notation = "/".join(slash_notation.split("/")[:2])
    possible_ids = get_possible_celex_ids(slash_notation, document_type, sector_id)

    queries = [f"{{ ?s owl:sameAs celex:{celex_id} . ?s owl:sameAs ?o }}" for celex_id in possible_ids]
    query = "SELECT * WHERE {" + " UNION ".join(queries) + "}"
    query = prepend_prefixes(query)

    results = run_query(query.strip())

    celex_ids: list[str] = []
    for binding in results["results"]["bindings"]:
        if "/celex/" in binding["o"]["value"]:
            celex_id = binding["o"]["value"].split("/")[-1]
            celex_ids.append(celex_id)

    return list(set(celex_ids))


@dataclass
class DocumentReference:
    """A reference to a EUR-Lex document with both CELEX ID and cellar URL.

    Attributes
    ----------
    cellar_url : str
        The cellar URL (always available, always works for fetching).
    celex_id : str | None
        The CELEX ID if valid, None if the ID is not in standard CELEX format.
    raw_id : str
        The raw identifier from SPARQL (may be CELEX, OJ reference, or other format).
    document_date : str
        The document date in ISO format (YYYY-MM-DD).
    """

    cellar_url: str
    celex_id: str | None
    raw_id: str
    document_date: str


def get_ids_and_urls_via_date(
    from_date: str,
    to_date: str | None = None,
    date_type: DateType | str = DateType.DOCUMENT,
) -> list[DocumentReference]:
    """Get document references for a date range via SPARQL.

    This function queries the EUR-Lex SPARQL endpoint to find documents
    published or modified within the specified date range. It returns
    both the CELEX ID (when valid) and the cellar URL for each document.

    The cellar URL is always usable for fetching, even when the CELEX ID
    is non-standard (e.g., OJ references like C/2026/00064 or IDs with
    revision suffixes like 32012L0029R(06)).

    Parameters
    ----------
    from_date : str
        Start date in ISO format (e.g., "2026-01-01").
    to_date : str, optional
        End date in ISO format. If not provided, defaults to from_date
        (single day query).
    date_type : DateType | str, optional
        Which date field to filter on. Options:
        - DateType.DOCUMENT / "document": Publication date (default)
        - DateType.MODIFIED / "modified": Last modification date
        - DateType.CREATED / "created": Creation date in CELLAR

        Use DateType.MODIFIED to find documents that have been updated,
        regardless of their original publication year. This is useful for
        catching amendments to old documents (e.g., a 2020 directive
        amended in 2026 will be found when querying 2026 modifications).

    Returns
    -------
    list[DocumentReference]
        List of document references, each containing:
        - cellar_url: Always available, use with get_html_by_cellar_url()
        - celex_id: Valid CELEX ID or None if format is non-standard
        - raw_id: The original ID from the query (may differ from celex_id)
        - document_date: The date matching the date_type filter

    Examples
    --------
    >>> # Get documents published on a specific date
    >>> docs = get_ids_and_urls_via_date("2026-01-15")  # doctest: +SKIP

    >>> # Get documents modified in January 2026 (includes old docs with updates)
    >>> docs = get_ids_and_urls_via_date(
    ...     "2026-01-01", "2026-01-31", date_type=DateType.MODIFIED
    ... )  # doctest: +SKIP

    >>> # Process results
    >>> for doc in docs:  # doctest: +SKIP
    ...     html = get_html_by_cellar_url(doc.cellar_url)
    """
    from eurlxp.parser import is_valid_celex_id

    if to_date is None:
        to_date = from_date

    # Convert string to DateType if needed
    if isinstance(date_type, str):
        date_type = DateType(date_type)

    # Map DateType to CDM predicate
    date_predicates = {
        DateType.DOCUMENT: "cdm:work_date_document",
        DateType.CREATED: "cdm:work_date_creation",
        DateType.MODIFIED: "cdm:work_date_lastUpdate",
    }
    date_predicate = date_predicates[date_type]

    query = f"""
SELECT ?work (STRAFTER(STR(?celexUri), "celex:") AS ?celexId) ?celexUri ?targetDate
WHERE {{
    ?work a cdm:work ;
        cdm:work_id_document ?celexUri ;
        {date_predicate} ?targetDate .

    FILTER(?targetDate >= "{from_date}"^^xsd:date &&
           ?targetDate <= "{to_date}"^^xsd:date &&
           regex(str(?celexUri), "celex"))
}}
ORDER BY DESC(?targetDate)"""

    query = prepend_prefixes(query)
    results = run_query(query.strip())

    documents: list[DocumentReference] = []

    for binding in results["results"]["bindings"]:
        raw_id = binding["celexId"]["value"]
        cellar_url = binding["work"]["value"]
        document_date = binding["targetDate"]["value"]

        # Validate CELEX ID - set to None if not standard format
        celex_id = raw_id if is_valid_celex_id(raw_id) else None

        documents.append(
            DocumentReference(
                cellar_url=cellar_url,
                celex_id=celex_id,
                raw_id=raw_id,
                document_date=document_date,
            )
        )

    return documents


def lookup_cellar_url(identifier: str) -> str | None:
    """Look up the cellar URL for any EUR-Lex identifier via SPARQL.

    This function queries the SPARQL endpoint to find the cellar URL
    for any identifier, including OJ references (like C/2026/00064)
    that are not valid CELEX IDs.

    Parameters
    ----------
    identifier : str
        Any EUR-Lex document identifier (CELEX ID, OJ reference, etc.).

    Returns
    -------
    str | None
        The cellar URL if found, None otherwise.

    Examples
    --------
    >>> url = lookup_cellar_url("C/2026/00064")  # doctest: +SKIP
    >>> url = lookup_cellar_url("32019R0947")  # doctest: +SKIP
    """
    # Query to find the work (cellar URL) for any identifier
    # The identifier might be in cdm:work_id_document or cdm:resource_legal_id_celex
    query = f"""
SELECT DISTINCT ?work
WHERE {{
    {{
        ?work cdm:work_id_document ?idUri .
        FILTER(CONTAINS(STR(?idUri), "{identifier}"))
    }}
    UNION
    {{
        ?work cdm:resource_legal_id_celex "{identifier}" .
    }}
}}
LIMIT 1"""

    query = prepend_prefixes(query)

    try:
        results = run_query(query.strip())

        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["work"]["value"]
    except Exception as e:
        logger.warning(f"SPARQL lookup failed for '{identifier}': {e}")

    return None


def get_regulations(limit: int = -1, shuffle: bool = False) -> list[str]:
    """Retrieve a list of CELLAR IDs for regulations from EUR-Lex.

    Parameters
    ----------
    limit : int
        The maximum number of regulations to retrieve. -1 for no limit.
    shuffle : bool
        Whether to shuffle the results.

    Returns
    -------
    list[str]
        A list of CELLAR IDs.

    Examples
    --------
    >>> cellar_ids = get_regulations(limit=5)  # doctest: +SKIP
    """
    from eurlxp.client import prepend_prefixes

    query = (
        "SELECT distinct ?doc WHERE { "
        "?doc cdm:work_has_resource-type <http://publications.europa.eu/resource/authority/resource-type/REG> "
        "}" + (" order by rand()" if shuffle else "") + (f" limit {limit}" if limit > 0 else "")
    )

    results = run_query(prepend_prefixes(query))

    cellar_ids: list[str] = []
    for result in results["results"]["bindings"]:
        cellar_ids.append(result["doc"]["value"].split("/")[-1])

    return cellar_ids


def get_documents(
    types: list[str] | None = None,
    limit: int = -1,
) -> list[dict[str, str]]:
    """Retrieve a list of documents of specified types from EUR-Lex.

    Parameters
    ----------
    types : list[str], optional
        The types of documents to return. Defaults to ["REG"].
        Examples: ["DIR", "DIR_IMPL", "DIR_DEL", "REG", "REG_IMPL", "REG_FINANC", "REG_DEL"]
    limit : int
        The maximum number of documents to retrieve. -1 for no limit.

    Returns
    -------
    list[dict[str, str]]
        A list of dicts containing 'celex', 'date', 'link', and 'type'.

    Examples
    --------
    >>> docs = get_documents(types=["REG"], limit=5)  # doctest: +SKIP
    """
    from eurlxp.client import prepend_prefixes

    if types is None:
        types = ["REG"]

    type_filters = " ||\n    ".join(
        f"?type=<http://publications.europa.eu/resource/authority/resource-type/{t}>" for t in types
    )

    query = f"""select distinct ?doc ?type ?celex ?date
where{{ ?doc cdm:work_has_resource-type ?type.
  FILTER(
    {type_filters}
  )
  FILTER(BOUND(?celex))
  OPTIONAL{{?doc cdm:resource_legal_id_celex ?celex.}}
  OPTIONAL{{?doc cdm:work_date_document ?date.}}
}}
"""
    if limit > 0:
        query += f"limit {limit}"

    query_results = run_query(prepend_prefixes(query))

    results: list[dict[str, str]] = []
    for result in query_results["results"]["bindings"]:
        results.append(
            {
                "celex": result.get("celex", {}).get("value", ""),
                "date": result.get("date", {}).get("value", ""),
                "link": result.get("doc", {}).get("value", ""),
                "type": result.get("type", {}).get("value", "").split("/")[-1],
            }
        )

    return results
