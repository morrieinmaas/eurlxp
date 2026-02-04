"""SPARQL query functions for EUR-Lex.

This module requires the optional `sparql` dependencies:
    pip install eurlxp[sparql]

The SPARQL endpoint (https://publications.europa.eu/webapi/rdf/sparql) is the recommended
way to query EUR-Lex data as it doesn't trigger bot detection like HTML scraping does.
"""

from __future__ import annotations
from eurlxp.client import prepend_prefixes
import logging
import time
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

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
    from parser import get_possible_celex_ids

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



def get_ids_and_urls_via_date(
    from_date: str, to_date: str| None = None
):
    """Gets a set of document with CELEX idts for a time dureation looking it up via EUR-Lex.

    Parameters
    ----------
    from_date : str
        The from date with dash format (e.g. 2026-01-01).
    document_type : str, optional
        The to date with dash format (e.g. 2026-01-01). If empty, set at same date as from, giving entries for just that day.
   
    Returns
    -------
    list[str] celex_ids_malformed
        A list of existing CELEX IDs, some diverting from the standatised shape, due to edits, version, etc..
    list[str] cellar_urls
        A list of urls, pointing to the matching celex-id-ed document, indentified via matching url ( that done, via specificities of the underlining EUR Lex system, as of 2026)
    """
    from eurlxp.client import prepend_prefixes

    if to_date == None:
        to_date = from_date

    query = f"""
SELECT ?work (STRAFTER(STR(?celexUri), "celex:") AS ?celexId) ?celexUri ?documentDate
WHERE {{
		?work a cdm:work ;
        cdm:work_id_document ?celexUri ;
        cdm:work_date_document ?documentDate .
  
  FILTER(?documentDate >= "{from_date}"^^xsd:date && 
         ?documentDate <= "{to_date}"^^xsd:date &&
         regex(str(?celexUri), "celex"))
}}
ORDER BY DESC(?documentDate)"""

    query = prepend_prefixes(query)
    results = run_query(query.strip())

    celex_ids_malformed: list[str]  = []
    celler_uuid_urls: list[str]  = []
    
    for binding in results["results"]["bindings"]:
        celex_id_maybe_malformed = binding["celexId"]["value"]
        celex_ids_malformed.append(celex_id_maybe_malformed)
        celler_url = binding["work"]["value"]
        celler_uuid_urls.append(celler_url)
    return celex_ids_malformed, celler_uuid_urls



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
