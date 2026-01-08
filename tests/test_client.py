"""Tests for the client module."""

import pytest

from eurlxp.client import prepend_prefixes, simplify_iri


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


class TestEURLexClient:
    """Tests for EURLexClient (requires network, marked as integration)."""

    @pytest.mark.integration
    def test_get_html_by_celex_id(self) -> None:
        from eurlxp.client import EURLexClient

        with EURLexClient() as client:
            html = client.get_html_by_celex_id("32019R0947")
            assert len(html) > 0
            assert "Article" in html


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.integration
    def test_get_html_by_celex_id_function(self) -> None:
        from eurlxp import get_html_by_celex_id

        html = get_html_by_celex_id("32019R0947")
        assert len(html) > 0
