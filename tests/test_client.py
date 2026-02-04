"""Tests for the client module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from eurlxp.client import (
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT,
    ClientConfig,
    EURLexClient,
    WAFChallengeError,
    _is_waf_challenge,
    detect_id_type,
    fetch_documents,
    get_default_config,
    get_html,
    get_html_by_cellar_url,
    prepend_prefixes,
    set_default_config,
    simplify_iri,
)


class TestPrefixes:
    """Tests for prefix handling functions."""

    def test_prepend_prefixes(self) -> None:
        query = "SELECT ?name WHERE { ?person rdf:name ?name }"
        result = prepend_prefixes(query)
        assert "prefix rdf:" in result
        assert "prefix cdm:" in result
        assert query in result

    def test_simplify_iri_with_known_prefix(self) -> None:
        iri = "http://publications.europa.eu/ontology/cdm#test"
        assert simplify_iri(iri) == "cdm:test"

    def test_simplify_iri_already_simplified(self) -> None:
        iri = "cdm:test"
        assert simplify_iri(iri) == "cdm:test"

    def test_simplify_iri_unknown_prefix(self) -> None:
        iri = "http://example.com/test"
        assert simplify_iri(iri) == "http://example.com/test"


class TestClientConfig:
    """Tests for ClientConfig dataclass."""

    def test_default_config_values(self) -> None:
        config = ClientConfig()
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.request_delay == DEFAULT_REQUEST_DELAY
        assert config.use_browser_headers is True
        assert config.raise_on_waf is True
        assert config.referer is None
        assert config.headers is None

    def test_get_headers_with_browser_headers(self) -> None:
        config = ClientConfig(use_browser_headers=True)
        headers = config.get_headers()
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

    def test_get_headers_with_minimal_headers(self) -> None:
        config = ClientConfig(use_browser_headers=False)
        headers = config.get_headers()
        assert "User-Agent" in headers
        assert "eurlxp" in headers["User-Agent"]

    def test_get_headers_with_custom_headers(self) -> None:
        config = ClientConfig(headers={"X-Custom": "test-value"})
        headers = config.get_headers()
        assert headers["X-Custom"] == "test-value"

    def test_get_headers_with_referer(self) -> None:
        config = ClientConfig(referer="https://example.com")
        headers = config.get_headers()
        assert headers["Referer"] == "https://example.com"


class TestGlobalConfig:
    """Tests for global configuration functions."""

    def test_get_default_config(self) -> None:
        config = get_default_config()
        assert isinstance(config, ClientConfig)

    def test_set_default_config(self) -> None:
        original = get_default_config()
        try:
            new_config = ClientConfig(request_delay=5.0)
            set_default_config(new_config)
            assert get_default_config().request_delay == 5.0
        finally:
            set_default_config(original)


class TestWAFDetection:
    """Tests for WAF challenge detection."""

    def test_is_waf_challenge_detects_awswaf(self) -> None:
        html = '<script src="https://example.awswaf.com/challenge.js"></script>'
        assert _is_waf_challenge(html) is True

    def test_is_waf_challenge_detects_integration(self) -> None:
        html = "<script>AwsWafIntegration.getToken()</script>"
        assert _is_waf_challenge(html) is True

    def test_is_waf_challenge_detects_noscript_message(self) -> None:
        html = "<noscript>verify that you're not a robot</noscript>"
        assert _is_waf_challenge(html) is True

    def test_is_waf_challenge_returns_false_for_normal_html(self) -> None:
        html = "<html><body><h1>Article 1</h1><p>Normal content</p></body></html>"
        assert _is_waf_challenge(html) is False

    def test_waf_challenge_error_message(self) -> None:
        error = WAFChallengeError()
        assert "AWS WAF" in str(error)


class TestEURLexClient:
    """Tests for EURLexClient."""

    def test_client_uses_config(self) -> None:
        config = ClientConfig(timeout=60.0, request_delay=1.0)
        client = EURLexClient(config=config)
        assert client._config.timeout == 60.0
        assert client._config.request_delay == 1.0

    def test_client_with_individual_params(self) -> None:
        client = EURLexClient(timeout=45.0, request_delay=2.0)
        assert client._config.timeout == 45.0
        assert client._config.request_delay == 2.0

    def test_client_rate_limiting(self) -> None:
        client = EURLexClient(request_delay=0.1)
        client._last_request_time = time.monotonic()
        start = time.monotonic()
        client._apply_rate_limit()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05  # Should have waited at least some time

    def test_client_raises_waf_error(self) -> None:
        waf_html = '<script src="https://awswaf.com/challenge.js"></script>'
        mock_response = MagicMock()
        mock_response.text = waf_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Disable sparql_fallback to test WAF error raising
            config = ClientConfig(sparql_fallback=False)
            client = EURLexClient(config=config)
            with pytest.raises(WAFChallengeError):
                client.get_html_by_celex_id("32019R0947")

    def test_client_does_not_raise_waf_when_disabled(self) -> None:
        waf_html = '<script src="https://awswaf.com/challenge.js"></script>'
        mock_response = MagicMock()
        mock_response.text = waf_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Disable both raise_on_waf and sparql_fallback to get raw HTML
            config = ClientConfig(raise_on_waf=False, sparql_fallback=False)
            client = EURLexClient(config=config)
            html = client.get_html_by_celex_id("32019R0947")
            assert "awswaf" in html

    def test_client_sparql_fallback_on_waf(self) -> None:
        waf_html = '<script src="https://awswaf.com/challenge.js"></script>'
        mock_response = MagicMock()
        mock_response.text = waf_html
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(EURLexClient, "_get_client") as mock_get_client,
            patch("eurlxp.client._fetch_html_via_sparql") as mock_sparql,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            mock_sparql.return_value = "<html><body>SPARQL fallback content</body></html>"

            config = ClientConfig(sparql_fallback=True)
            client = EURLexClient(config=config)
            html = client.get_html_by_celex_id("32019R0947")
            assert "SPARQL fallback content" in html
            mock_sparql.assert_called_once_with("32019R0947", "en")

    def test_sparql_fallback_config_default_true(self) -> None:
        config = ClientConfig()
        assert config.sparql_fallback is True

    @pytest.mark.integration
    def test_get_html_by_celex_id_integration(self) -> None:
        """Integration test - may raise WAFChallengeError if blocked."""
        with EURLexClient() as client:
            try:
                html = client.get_html_by_celex_id("32019R0947")
                assert len(html) > 0
            except WAFChallengeError:
                pytest.skip("EUR-Lex is blocking requests with WAF challenge")


class TestGetHtmlByCellarUrl:
    """Tests for cellar URL fetching."""

    def test_get_html_by_cellar_url_method(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Document content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            client = EURLexClient()
            html = client.get_html_by_cellar_url("http://publications.europa.eu/resource/cellar/abc123-def456")
            assert "Document content" in html

    def test_get_html_by_cellar_url_applies_rate_limit(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            client = EURLexClient(request_delay=0.1)
            client._last_request_time = time.monotonic()
            start = time.monotonic()
            client.get_html_by_cellar_url("http://publications.europa.eu/resource/cellar/abc123")
            elapsed = time.monotonic() - start
            assert elapsed >= 0.05  # Should have waited

    def test_get_html_by_cellar_url_raises_waf_error(self) -> None:
        waf_html = '<script src="https://awswaf.com/challenge.js"></script>'
        mock_response = MagicMock()
        mock_response.text = waf_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            config = ClientConfig(sparql_fallback=False)
            client = EURLexClient(config=config)
            with pytest.raises(WAFChallengeError):
                client.get_html_by_cellar_url("http://publications.europa.eu/resource/cellar/abc123")

    def test_get_html_by_cellar_url_convenience_function(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            html = get_html_by_cellar_url("http://publications.europa.eu/resource/cellar/abc123")
            assert "Content" in html

    def test_get_html_by_cellar_url_handles_url_with_suffix(self) -> None:
        """Test URLs with suffixes like /DOC_1."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Document</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            client = EURLexClient()
            html = client.get_html_by_cellar_url("http://publications.europa.eu/resource/cellar/abc123/DOC_1")
            assert "Document" in html


class TestDetectIdType:
    """Tests for detect_id_type function."""

    def test_detect_cellar_url(self) -> None:
        assert detect_id_type("http://publications.europa.eu/resource/cellar/abc123") == "cellar_url"
        assert detect_id_type("https://publications.europa.eu/resource/cellar/abc123") == "cellar_url"

    def test_detect_celex_id(self) -> None:
        assert detect_id_type("32019R0947") == "celex"
        assert detect_id_type("52026XG00745") == "celex"
        assert detect_id_type("32012L0029R(06)") == "celex"

    def test_detect_cellar_id_with_prefix(self) -> None:
        assert detect_id_type("cellar:abc-123-def") == "cellar_id"

    def test_detect_cellar_id_uuid(self) -> None:
        # UUID format: 8-4-4-4-12 characters
        assert detect_id_type("12345678-1234-1234-1234-123456789012") == "cellar_id"

    def test_detect_oj_reference(self) -> None:
        # OJ references like C/2024/03709 are detected and fetched via SPARQL
        assert detect_id_type("C/2026/00064") == "oj_reference"
        assert detect_id_type("L/2024/01234") == "oj_reference"
        assert detect_id_type("CA/2024/00001") == "oj_reference"

    def test_detect_unknown_random_string(self) -> None:
        assert detect_id_type("random-string") == "unknown"


class TestGetHtml:
    """Tests for get_html unified function."""

    def test_get_html_with_celex_id(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>CELEX content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            html = get_html("32019R0947")
            assert "CELEX content" in html

    def test_get_html_with_cellar_url(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Cellar URL content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            html = get_html("http://publications.europa.eu/resource/cellar/abc123")
            assert "Cellar URL content" in html

    def test_get_html_with_oj_reference_uses_sparql_lookup(self) -> None:
        """OJ references are looked up via SPARQL."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>OJ content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(EURLexClient, "_get_client") as mock_get_client,
            patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            mock_lookup.return_value = "http://publications.europa.eu/resource/cellar/abc123"

            html = get_html("C/2026/00064")
            assert "OJ content" in html
            mock_lookup.assert_called_once_with("C/2026/00064")

    def test_get_html_with_unknown_raises_error_when_sparql_fails(self) -> None:
        """If SPARQL lookup returns None, a ValueError is raised."""
        with patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup:
            mock_lookup.return_value = None

            with pytest.raises(ValueError, match="SPARQL lookup found no results"):
                get_html("invalid-id-12345")


class TestFetchDocuments:
    """Tests for fetch_documents batch function."""

    def test_fetch_documents_mixed_types(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            results = fetch_documents(
                [
                    "32019R0947",  # CELEX
                    "http://publications.europa.eu/resource/cellar/abc123",  # URL
                ]
            )
            assert len(results) == 2
            assert "32019R0947" in results
            assert "http://publications.europa.eu/resource/cellar/abc123" in results

    def test_fetch_documents_skip_errors(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(EURLexClient, "_get_client") as mock_get_client,
            patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            # SPARQL lookup fails, so unknown ID will be skipped
            mock_lookup.return_value = None

            # Include an unknown ID type that will be skipped
            results = fetch_documents(
                [
                    "32019R0947",
                    "invalid-id-12345",  # Unknown type, SPARQL fails - will be skipped
                ],
                on_error="skip",
            )

            assert len(results) == 1
            assert "32019R0947" in results

    def test_fetch_documents_include_errors(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(EURLexClient, "_get_client") as mock_get_client,
            patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            # SPARQL lookup fails
            mock_lookup.return_value = None

            results = fetch_documents(
                [
                    "32019R0947",
                    "invalid-id-12345",  # Unknown type, SPARQL fails
                ],
                on_error="include",
            )

            assert len(results) == 2
            assert isinstance(results["32019R0947"], str)
            assert isinstance(results["invalid-id-12345"], Exception)

    def test_fetch_documents_raise_errors(self) -> None:
        with (
            patch.object(EURLexClient, "_get_client"),
            patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup,
            pytest.raises(ValueError),
        ):
            mock_lookup.return_value = None
            fetch_documents(["invalid-id-12345"], on_error="raise")

    def test_fetch_documents_with_oj_reference(self) -> None:
        """OJ references are fetched via SPARQL lookup."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>OJ content</body></html>"
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(EURLexClient, "_get_client") as mock_get_client,
            patch("eurlxp.sparql.lookup_cellar_url") as mock_lookup,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            mock_lookup.return_value = "http://publications.europa.eu/resource/cellar/abc123"

            results = fetch_documents(["C/2026/00064"])

            assert len(results) == 1
            assert "C/2026/00064" in results
            assert "OJ content" in results["C/2026/00064"]
            mock_lookup.assert_called_once_with("C/2026/00064")


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.integration
    def test_get_html_by_celex_id_function(self) -> None:
        from eurlxp import WAFChallengeError, get_html_by_celex_id

        try:
            html = get_html_by_celex_id("32019R0947")
            assert len(html) > 0
        except WAFChallengeError:
            pytest.skip("EUR-Lex is blocking requests with WAF challenge")


class TestRetryLogic:
    """Tests for HTTP retry logic on transient errors."""

    def test_client_config_has_retry_defaults(self) -> None:
        """ClientConfig should have default retry settings."""
        from eurlxp.client import (
            DEFAULT_MAX_RETRIES,
            DEFAULT_RETRY_BACKOFF,
            DEFAULT_RETRY_DELAY,
        )

        config = ClientConfig()
        assert config.max_retries == DEFAULT_MAX_RETRIES
        assert config.retry_delay == DEFAULT_RETRY_DELAY
        assert config.retry_backoff == DEFAULT_RETRY_BACKOFF

    def test_client_config_custom_retry_settings(self) -> None:
        """ClientConfig should accept custom retry settings."""
        config = ClientConfig(max_retries=5, retry_delay=3.0, retry_backoff=3.0)
        assert config.max_retries == 5
        assert config.retry_delay == 3.0
        assert config.retry_backoff == 3.0

    def test_retry_on_500_error(self) -> None:
        """Client should retry on HTTP 500 errors."""
        import httpx

        from eurlxp.client import RETRYABLE_STATUS_CODES

        assert 500 in RETRYABLE_STATUS_CODES

        # Create a mock that fails twice then succeeds
        call_count = 0
        mock_response_success = MagicMock()
        mock_response_success.text = "<html>Success</html>"
        mock_response_success.raise_for_status = MagicMock()

        mock_response_error = MagicMock()
        mock_response_error.status_code = 500

        def mock_get(_url: str) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response_error)
                raise error
            return mock_response_success

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = mock_get
            mock_get_client.return_value = mock_client

            # Use minimal retry delay for faster test
            config = ClientConfig(max_retries=3, retry_delay=0.01, retry_backoff=1.0)
            with EURLexClient(config=config) as client:
                html = client.get_html_by_celex_id("32019R0947")
                assert "Success" in html
                assert call_count == 3  # 2 failures + 1 success

    def test_retry_exhausted_raises_error(self) -> None:
        """Client should raise error after max retries."""
        import httpx

        mock_response_error = MagicMock()
        mock_response_error.status_code = 500

        def mock_get(_url: str) -> None:
            error = httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response_error)
            raise error

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = mock_get
            mock_get_client.return_value = mock_client

            # Use minimal retry delay for faster test
            config = ClientConfig(max_retries=2, retry_delay=0.01, retry_backoff=1.0)
            with EURLexClient(config=config) as client, pytest.raises(httpx.HTTPStatusError):
                client.get_html_by_celex_id("32019R0947")

    def test_no_retry_on_non_retryable_error(self) -> None:
        """Client should not retry on non-retryable errors (e.g., 404)."""
        import httpx

        from eurlxp.client import RETRYABLE_STATUS_CODES

        assert 404 not in RETRYABLE_STATUS_CODES

        call_count = 0
        mock_response_error = MagicMock()
        mock_response_error.status_code = 404

        def mock_get(_url: str) -> None:
            nonlocal call_count
            call_count += 1
            error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response_error)
            raise error

        with patch.object(EURLexClient, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = mock_get
            mock_get_client.return_value = mock_client

            config = ClientConfig(max_retries=3, retry_delay=0.01)
            with EURLexClient(config=config) as client, pytest.raises(httpx.HTTPStatusError):
                client.get_html_by_celex_id("32019R0947")

            # Should only have called once (no retries)
            assert call_count == 1

    def test_retry_on_502_503_504_errors(self) -> None:
        """Client should retry on all retryable status codes."""
        from eurlxp.client import RETRYABLE_STATUS_CODES

        assert 502 in RETRYABLE_STATUS_CODES
        assert 503 in RETRYABLE_STATUS_CODES
        assert 504 in RETRYABLE_STATUS_CODES
