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
    get_default_config,
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
