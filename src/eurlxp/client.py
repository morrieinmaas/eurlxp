"""HTTP client for fetching EUR-Lex documents."""

from __future__ import annotations

import httpx

from eurlxp.models import EURLEX_PREFIXES

# Base URLs for EUR-Lex resources
# Note: The old publications.europa.eu/resource/celex/ HTML endpoints return 400 errors
# Using the direct EUR-Lex HTML endpoints instead
EURLEX_HTML_URL = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex_id}"
EURLEX_CELLAR_URL = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELLAR:{cellar_id}"
# Cellar SPARQL endpoint (official, still current)
# Note: As of Oct 2023, OJ is published act-by-act instead of as collections
# See: https://op.europa.eu/en/web/cellar/the-official-journal-act-by-act
EURLEX_SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"

# Default headers for HTML requests
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "User-Agent": "eurlxp/0.1.0 (https://github.com/morrieinmaas/eurlxp)",
}

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0


class EURLexClient:
    """Synchronous HTTP client for EUR-Lex API."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> EURLexClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_html_by_celex_id(self, celex_id: str, language: str = "en") -> str:
        """Fetch HTML document by CELEX ID.

        Parameters
        ----------
        celex_id : str
            The CELEX identifier (e.g., "32019R0947").
        language : str
            Language code (default: "en").

        Returns
        -------
        str
            The HTML content of the document.

        Examples
        --------
        >>> client = EURLexClient()
        >>> html = client.get_html_by_celex_id("32019R0947")
        >>> len(html) > 0
        True
        """
        lang_code = language.upper()
        url = EURLEX_HTML_URL.format(lang=lang_code, celex_id=celex_id)
        response = self._get_client().get(url)
        response.raise_for_status()
        return response.text

    def get_html_by_cellar_id(self, cellar_id: str, language: str = "en") -> str:
        """Fetch HTML document by CELLAR ID.

        Parameters
        ----------
        cellar_id : str
            The CELLAR identifier.
        language : str
            Language code (default: "en").

        Returns
        -------
        str
            The HTML content of the document.
        """
        clean_id = cellar_id.split(":")[1] if ":" in cellar_id else cellar_id
        lang_code = language.upper()
        url = EURLEX_CELLAR_URL.format(lang=lang_code, cellar_id=clean_id)
        response = self._get_client().get(url)
        response.raise_for_status()
        return response.text


class AsyncEURLexClient:
    """Asynchronous HTTP client for EUR-Lex API."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._timeout = timeout
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._headers,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AsyncEURLexClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def get_html_by_celex_id(self, celex_id: str, language: str = "en") -> str:
        """Fetch HTML document by CELEX ID asynchronously.

        Parameters
        ----------
        celex_id : str
            The CELEX identifier (e.g., "32019R0947").
        language : str
            Language code (default: "en").

        Returns
        -------
        str
            The HTML content of the document.
        """
        lang_code = language.upper()
        url = EURLEX_HTML_URL.format(lang=lang_code, celex_id=celex_id)
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    async def get_html_by_cellar_id(self, cellar_id: str, language: str = "en") -> str:
        """Fetch HTML document by CELLAR ID asynchronously.

        Parameters
        ----------
        cellar_id : str
            The CELLAR identifier.
        language : str
            Language code (default: "en").

        Returns
        -------
        str
            The HTML content of the document.
        """
        clean_id = cellar_id.split(":")[1] if ":" in cellar_id else cellar_id
        lang_code = language.upper()
        url = EURLEX_CELLAR_URL.format(lang=lang_code, cellar_id=clean_id)
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    async def fetch_multiple(
        self,
        celex_ids: list[str],
        language: str = "en",
    ) -> dict[str, str]:
        """Fetch multiple documents concurrently.

        Parameters
        ----------
        celex_ids : list[str]
            List of CELEX identifiers.
        language : str
            Language code (default: "en").

        Returns
        -------
        dict[str, str]
            Mapping from CELEX ID to HTML content.
        """
        import asyncio

        async def fetch_one(celex_id: str) -> tuple[str, str | Exception]:
            try:
                html = await self.get_html_by_celex_id(celex_id, language)
                return celex_id, html
            except Exception as e:
                return celex_id, e

        results = await asyncio.gather(*[fetch_one(cid) for cid in celex_ids])
        return {cid: html for cid, html in results if isinstance(html, str)}


def get_html_by_celex_id(celex_id: str, language: str = "en") -> str:
    """Convenience function to fetch HTML by CELEX ID.

    This is a drop-in replacement for the original eurlex package function.

    Parameters
    ----------
    celex_id : str
        The CELEX identifier (e.g., "32019R0947").
    language : str
        Language code (default: "en").

    Returns
    -------
    str
        The HTML content of the document.

    Examples
    --------
    >>> html = get_html_by_celex_id("32019R0947")
    >>> "Article" in html
    True
    """
    with EURLexClient() as client:
        return client.get_html_by_celex_id(celex_id, language)


def get_html_by_cellar_id(cellar_id: str, language: str = "en") -> str:
    """Convenience function to fetch HTML by CELLAR ID.

    Parameters
    ----------
    cellar_id : str
        The CELLAR identifier.
    language : str
        Language code (default: "en").

    Returns
    -------
    str
        The HTML content of the document.
    """
    with EURLexClient() as client:
        return client.get_html_by_cellar_id(cellar_id, language)


def prepend_prefixes(query: str) -> str:
    """Prepend SPARQL query with EUR-Lex prefixes.

    Parameters
    ----------
    query : str
        The SPARQL query.

    Returns
    -------
    str
        Query with prefixes prepended.

    Examples
    --------
    >>> 'prefix rdf' in prepend_prefixes("SELECT ?name WHERE { ?person rdf:name ?name }")
    True
    """
    prefix_lines = [f"prefix {prefix}: <{url}>" for prefix, url in EURLEX_PREFIXES.items()]
    return "\n".join(prefix_lines) + " " + query


def simplify_iri(iri: str) -> str:
    """Simplify an IRI by replacing known prefixes.

    Parameters
    ----------
    iri : str
        The IRI to simplify.

    Returns
    -------
    str
        Simplified IRI with prefix notation.

    Examples
    --------
    >>> simplify_iri("http://publications.europa.eu/ontology/cdm#test")
    'cdm:test'
    >>> simplify_iri("cdm:test")
    'cdm:test'
    """
    for prefix, url in EURLEX_PREFIXES.items():
        if iri.startswith(url):
            return f"{prefix}:{iri[len(url) :]}"
    return iri
