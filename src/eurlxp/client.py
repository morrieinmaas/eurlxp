"""HTTP client for fetching EUR-Lex documents."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from eurlxp.models import EURLEX_PREFIXES

logger = logging.getLogger(__name__)


class WAFChallengeError(Exception):
    """Raised when EUR-Lex returns an AWS WAF JavaScript challenge.

    This indicates that the request was blocked by bot detection.
    Solutions:
    1. Use the SPARQL endpoint instead (run_query, get_documents, etc.)
    2. Add delays between requests with request_delay parameter
    3. Use a browser automation tool like Playwright
    """

    def __init__(
        self, message: str = "EUR-Lex returned an AWS WAF challenge. See WAFChallengeError docs for solutions."
    ):
        super().__init__(message)


def _is_waf_challenge(html: str) -> bool:
    """Check if the response is an AWS WAF JavaScript challenge."""
    waf_indicators = [
        "awswaf.com",
        "AwsWafIntegration",
        "challenge.js",
        "JavaScript is disabled",
        "verify that you're not a robot",
    ]
    return any(indicator in html for indicator in waf_indicators)


def _fetch_html_via_sparql(celex_id: str, language: str = "en") -> str:  # noqa: ARG001
    """Fetch document content via SPARQL as fallback when HTML scraping is blocked.

    This returns a simplified HTML representation built from SPARQL metadata.
    It won't have the full document structure but provides the core content.

    Parameters
    ----------
    celex_id : str
        The CELEX identifier.
    language : str
        Language code (default: "en").

    Returns
    -------
    str
        HTML content reconstructed from SPARQL data.

    Raises
    ------
    ImportError
        If SPARQL dependencies are not installed.
    """
    try:
        import pandas as pd

        from eurlxp.sparql import get_celex_dataframe
    except ImportError as e:
        raise ImportError(
            "SPARQL fallback requires sparql dependencies. Install with: pip install eurlxp[sparql]"
        ) from e

    logger.info("Falling back to SPARQL for CELEX ID: %s", celex_id)

    try:
        df: pd.DataFrame = get_celex_dataframe(celex_id)

        # Build a minimal HTML representation from the RDF data
        title = celex_id

        # Extract title if available
        if len(df) > 0 and "o" in df.columns:
            title_rows = df[df["o"].str.contains("title", case=False, na=False)]
            if len(title_rows) > 0 and "p" in df.columns:
                title = str(title_rows.iloc[0]["p"])

        # Build HTML
        html = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
    <p class="doc-ti">{title}</p>
    <p class="normal">Document retrieved via SPARQL fallback (CELEX: {celex_id})</p>
    <p class="normal">Full HTML content unavailable due to bot detection.</p>
    <p class="normal">Use get_celex_dataframe("{celex_id}") for complete RDF metadata.</p>
</body>
</html>"""
        return html

    except Exception as e:
        logger.error("SPARQL fallback failed for CELEX ID %s: %s", celex_id, e)
        raise WAFChallengeError(
            f"Both HTML scraping and SPARQL fallback failed for CELEX ID '{celex_id}'. SPARQL error: {e}"
        ) from e


# Base URLs for EUR-Lex resources
# Note: The old publications.europa.eu/resource/celex/ HTML endpoints return 400 errors
# Using the direct EUR-Lex HTML endpoints instead
EURLEX_HTML_URL = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex_id}"
EURLEX_CELLAR_URL = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELLAR:{cellar_id}"
# Cellar SPARQL endpoint (official, still current)
# Note: As of Oct 2023, OJ is published act-by-act instead of as collections
# See: https://op.europa.eu/en/web/cellar/the-official-journal-act-by-act
EURLEX_SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"

# Default headers for HTML requests - designed to avoid bot detection
# These mimic a real browser to prevent AWS WAF blocking
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Minimal headers for users who prefer transparency
MINIMAL_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "User-Agent": "eurlxp/0.2.5 (https://github.com/morrieinmaas/eurlxp)",
}

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0

# Default delay between requests in seconds (rate limiting)
DEFAULT_REQUEST_DELAY = 0.0

# Whether to raise an exception on WAF challenge (default: True)
# Set to False to return the challenge HTML instead
DEFAULT_RAISE_ON_WAF = True

# Whether to fallback to SPARQL when WAF challenge is detected (default: False)
# When True, attempts to fetch document metadata via SPARQL instead of raising
DEFAULT_SPARQL_FALLBACK = True


@dataclass
class ClientConfig:
    """Configuration for EUR-Lex HTTP clients.

    Attributes
    ----------
    timeout : float
        Request timeout in seconds (default: 30.0).
    headers : dict[str, str] | None
        Custom headers to merge with defaults. Set to empty dict to use only defaults.
    request_delay : float
        Delay between requests in seconds for rate limiting (default: 0.0).
    use_browser_headers : bool
        If True (default), use browser-like headers to avoid bot detection.
        If False, use minimal transparent headers.
    referer : str | None
        Optional referer header to include in requests.
    raise_on_waf : bool
        If True (default), raise WAFChallengeError when bot detection is triggered.
        If False, return the challenge HTML instead (unless sparql_fallback is True).
    sparql_fallback : bool
        If True, automatically fallback to SPARQL endpoint when WAF challenge is detected.
        Returns a minimal HTML representation of the document from SPARQL metadata.
        Requires `eurlxp[sparql]` dependencies. Default: False.

    Examples
    --------
    >>> config = ClientConfig(request_delay=2.0)  # 2 second delay between requests
    >>> config = ClientConfig(use_browser_headers=False)  # Use minimal headers
    >>> config = ClientConfig(headers={"X-Custom": "value"})  # Add custom headers
    >>> config = ClientConfig(raise_on_waf=False)  # Don't raise on WAF challenge
    >>> config = ClientConfig(sparql_fallback=True)  # Auto-fallback to SPARQL on WAF
    """

    timeout: float = DEFAULT_TIMEOUT
    headers: dict[str, str] | None = None
    request_delay: float = DEFAULT_REQUEST_DELAY
    use_browser_headers: bool = True
    referer: str | None = None
    raise_on_waf: bool = DEFAULT_RAISE_ON_WAF
    sparql_fallback: bool = DEFAULT_SPARQL_FALLBACK

    def get_headers(self) -> dict[str, str]:
        """Build the final headers dict."""
        base = DEFAULT_HEADERS.copy() if self.use_browser_headers else MINIMAL_HEADERS.copy()
        if self.referer:
            base["Referer"] = self.referer
        if self.headers:
            base.update(self.headers)
        return base


# Global default configuration
_default_config: ClientConfig = ClientConfig()


def get_default_config() -> ClientConfig:
    """Get the current default client configuration."""
    return _default_config


def set_default_config(config: ClientConfig) -> None:
    """Set the default client configuration globally.

    Parameters
    ----------
    config : ClientConfig
        The configuration to use as default.

    Examples
    --------
    >>> set_default_config(ClientConfig(request_delay=1.0, use_browser_headers=True))
    """
    global _default_config
    _default_config = config


class EURLexClient:
    """Synchronous HTTP client for EUR-Lex API.

    Parameters
    ----------
    timeout : float
        Request timeout in seconds (default: 30.0).
    headers : dict[str, str] | None
        Custom headers to merge with defaults.
    request_delay : float
        Delay between requests in seconds for rate limiting (default: 0.0).
    config : ClientConfig | None
        Full configuration object. If provided, overrides other parameters.

    Examples
    --------
    >>> # Basic usage
    >>> with EURLexClient() as client:
    ...     html = client.get_html_by_celex_id("32019R0947")

    >>> # With rate limiting to avoid bot detection
    >>> with EURLexClient(request_delay=2.0) as client:
    ...     html = client.get_html_by_celex_id("32019R0947")

    >>> # With custom configuration
    >>> config = ClientConfig(request_delay=1.0, use_browser_headers=True)
    >>> with EURLexClient(config=config) as client:
    ...     html = client.get_html_by_celex_id("32019R0947")
    """

    def __init__(
        self,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
        request_delay: float | None = None,
        config: ClientConfig | None = None,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            base_config = get_default_config()
            self._config = ClientConfig(
                timeout=timeout if timeout is not None else base_config.timeout,
                headers={**base_config.get_headers(), **(headers or {})},
                request_delay=request_delay if request_delay is not None else base_config.request_delay,
                use_browser_headers=base_config.use_browser_headers,
                referer=base_config.referer,
            )
        self._client: httpx.Client | None = None
        self._last_request_time: float = 0.0

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._config.timeout,
                headers=self._config.get_headers(),
                follow_redirects=True,
            )
        return self._client

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay if configured."""
        if self._config.request_delay > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._config.request_delay:
                time.sleep(self._config.request_delay - elapsed)
        self._last_request_time = time.monotonic()

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

        Raises
        ------
        WAFChallengeError
            If EUR-Lex returns a bot detection challenge (when raise_on_waf=True).
        """
        self._apply_rate_limit()
        lang_code = language.upper()
        url = EURLEX_HTML_URL.format(lang=lang_code, celex_id=celex_id)
        response = self._get_client().get(url)
        response.raise_for_status()
        html = response.text
        if _is_waf_challenge(html):
            logger.warning("WAF challenge detected for CELEX ID: %s", celex_id)
            if self._config.sparql_fallback:
                return _fetch_html_via_sparql(celex_id, language)
            if self._config.raise_on_waf:
                raise WAFChallengeError(
                    f"EUR-Lex returned an AWS WAF challenge for CELEX ID '{celex_id}'. "
                    "Try using SPARQL functions (get_documents, run_query) instead, "
                    "or set sparql_fallback=True for automatic fallback."
                )
        return html

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

        Raises
        ------
        WAFChallengeError
            If EUR-Lex returns a bot detection challenge (when raise_on_waf=True).
        """
        self._apply_rate_limit()
        clean_id = cellar_id.split(":")[1] if ":" in cellar_id else cellar_id
        lang_code = language.upper()
        url = EURLEX_CELLAR_URL.format(lang=lang_code, cellar_id=clean_id)
        response = self._get_client().get(url)
        response.raise_for_status()
        html = response.text
        if _is_waf_challenge(html):
            logger.warning("WAF challenge detected for CELLAR ID: %s", cellar_id)
            # Note: SPARQL fallback for CELLAR IDs would need CELEX lookup first
            # For now, just raise the error with guidance
            if self._config.raise_on_waf:
                raise WAFChallengeError(
                    f"EUR-Lex returned an AWS WAF challenge for CELLAR ID '{cellar_id}'. "
                    "Try using SPARQL functions (get_documents, run_query) instead, "
                    "or use get_html_by_celex_id with sparql_fallback=True."
                )
        return html


class AsyncEURLexClient:
    """Asynchronous HTTP client for EUR-Lex API.

    Parameters
    ----------
    timeout : float
        Request timeout in seconds (default: 30.0).
    headers : dict[str, str] | None
        Custom headers to merge with defaults.
    request_delay : float
        Delay between requests in seconds for rate limiting (default: 0.0).
    config : ClientConfig | None
        Full configuration object. If provided, overrides other parameters.

    Examples
    --------
    >>> async with AsyncEURLexClient() as client:
    ...     html = await client.get_html_by_celex_id("32019R0947")

    >>> # With rate limiting
    >>> async with AsyncEURLexClient(request_delay=2.0) as client:
    ...     docs = await client.fetch_multiple(["32019R0947", "32019R0945"])
    """

    def __init__(
        self,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
        request_delay: float | None = None,
        config: ClientConfig | None = None,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            base_config = get_default_config()
            self._config = ClientConfig(
                timeout=timeout if timeout is not None else base_config.timeout,
                headers={**base_config.get_headers(), **(headers or {})},
                request_delay=request_delay if request_delay is not None else base_config.request_delay,
                use_browser_headers=base_config.use_browser_headers,
                referer=base_config.referer,
            )
        self._client: httpx.AsyncClient | None = None
        self._last_request_time: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout,
                headers=self._config.get_headers(),
                follow_redirects=True,
            )
        return self._client

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay if configured."""
        import asyncio

        if self._config.request_delay > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._config.request_delay:
                await asyncio.sleep(self._config.request_delay - elapsed)
        self._last_request_time = time.monotonic()

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

        Raises
        ------
        WAFChallengeError
            If EUR-Lex returns a bot detection challenge (when raise_on_waf=True).
        """
        await self._apply_rate_limit()
        lang_code = language.upper()
        url = EURLEX_HTML_URL.format(lang=lang_code, celex_id=celex_id)
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        if _is_waf_challenge(html):
            logger.warning("WAF challenge detected for CELEX ID: %s", celex_id)
            if self._config.sparql_fallback:
                return _fetch_html_via_sparql(celex_id, language)
            if self._config.raise_on_waf:
                raise WAFChallengeError(
                    f"EUR-Lex returned an AWS WAF challenge for CELEX ID '{celex_id}'. "
                    "Try using SPARQL functions (get_documents, run_query) instead, "
                    "or set sparql_fallback=True for automatic fallback."
                )
        return html

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

        Raises
        ------
        WAFChallengeError
            If EUR-Lex returns a bot detection challenge (when raise_on_waf=True).
        """
        await self._apply_rate_limit()
        clean_id = cellar_id.split(":")[1] if ":" in cellar_id else cellar_id
        lang_code = language.upper()
        url = EURLEX_CELLAR_URL.format(lang=lang_code, cellar_id=clean_id)
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        if _is_waf_challenge(html):
            logger.warning("WAF challenge detected for CELLAR ID: %s", cellar_id)
            if self._config.raise_on_waf:
                raise WAFChallengeError(
                    f"EUR-Lex returned an AWS WAF challenge for CELLAR ID '{cellar_id}'. "
                    "Try using SPARQL functions (get_documents, run_query) instead, "
                    "or use get_html_by_celex_id with sparql_fallback=True."
                )
        return html

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
