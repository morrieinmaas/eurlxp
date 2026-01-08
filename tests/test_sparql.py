"""Tests for the SPARQL module."""

from unittest.mock import MagicMock, patch

import pytest

from eurlxp.sparql import convert_sparql_output_to_dataframe


class TestConvertSparqlOutputToDataframe:
    """Tests for convert_sparql_output_to_dataframe."""

    def test_basic_conversion(self) -> None:
        sparql_results = {"results": {"bindings": [{"subject": {"value": "http://example.com/test"}}]}}
        df = convert_sparql_output_to_dataframe(sparql_results)
        assert len(df) == 1
        assert "subject" in df.columns

    def test_empty_results(self) -> None:
        sparql_results = {"results": {"bindings": []}}
        df = convert_sparql_output_to_dataframe(sparql_results)
        assert len(df) == 0

    def test_multiple_columns(self) -> None:
        sparql_results = {
            "results": {
                "bindings": [
                    {"s": {"value": "http://example.com/s1"}, "p": {"value": "http://example.com/p1"}},
                    {"s": {"value": "http://example.com/s2"}, "p": {"value": "http://example.com/p2"}},
                ]
            }
        }
        df = convert_sparql_output_to_dataframe(sparql_results)
        assert len(df) == 2
        assert "s" in df.columns
        assert "p" in df.columns

    def test_simplifies_cdm_iri(self) -> None:
        sparql_results = {
            "results": {"bindings": [{"subject": {"value": "http://publications.europa.eu/ontology/cdm#test"}}]}
        }
        df = convert_sparql_output_to_dataframe(sparql_results)
        assert df.iloc[0]["subject"] == "cdm:test"


class TestRunQuery:
    """Tests for run_query (mocked)."""

    @pytest.mark.integration
    def test_run_query_requires_sparql_deps(self) -> None:
        from eurlxp.sparql import run_query

        # This will either work (if deps installed) or raise ImportError
        try:
            result = run_query("SELECT ?s WHERE { ?s ?p ?o } LIMIT 1")
            assert "results" in result
        except ImportError:
            pytest.skip("SPARQL dependencies not installed")

    def test_run_query_mocked(self) -> None:
        # This test verifies the function structure by mocking the SPARQLWrapper import
        mock_sparql_instance = MagicMock()
        mock_sparql_instance.query.return_value.convert.return_value = {"results": {"bindings": []}}

        mock_sparql_class = MagicMock(return_value=mock_sparql_instance)
        mock_sparql_module = MagicMock()
        mock_sparql_module.SPARQLWrapper = mock_sparql_class
        mock_sparql_module.JSON = "json"

        with (
            patch("eurlxp.sparql._check_sparql_dependencies"),
            patch.dict("sys.modules", {"SPARQLWrapper": mock_sparql_module}),
        ):
            from importlib import reload

            from eurlxp import sparql

            reload(sparql)
            result = sparql.run_query("SELECT ?s WHERE { ?s ?p ?o }")
            assert result == {"results": {"bindings": []}}


class TestGetCelexDataframe:
    """Tests for get_celex_dataframe (mocked)."""

    @pytest.mark.integration
    def test_get_celex_dataframe_integration(self) -> None:
        try:
            from eurlxp.sparql import get_celex_dataframe

            df = get_celex_dataframe("32019R0947")
            assert len(df) > 0
        except ImportError:
            pytest.skip("SPARQL dependencies not installed")


class TestGuesscelexIdsViaEurlex:
    """Tests for guess_celex_ids_via_eurlex (mocked)."""

    def test_guess_celex_ids_mocked(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {"o": {"value": "http://publications.europa.eu/resource/celex/32019R0947"}},
                    ]
                }
            }

            from eurlxp.sparql import guess_celex_ids_via_eurlex

            result = guess_celex_ids_via_eurlex("2019/947")
            assert "32019R0947" in result


class TestGetRegulations:
    """Tests for get_regulations (mocked)."""

    def test_get_regulations_mocked(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {"doc": {"value": "http://publications.europa.eu/resource/cellar/abc123"}},
                        {"doc": {"value": "http://publications.europa.eu/resource/cellar/def456"}},
                    ]
                }
            }

            from eurlxp.sparql import get_regulations

            result = get_regulations(limit=2)
            assert len(result) == 2
            assert "abc123" in result
            assert "def456" in result


class TestGetDocuments:
    """Tests for get_documents (mocked)."""

    def test_get_documents_mocked(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {
                            "doc": {"value": "http://example.com/doc1"},
                            "type": {"value": "http://example.com/REG"},
                            "celex": {"value": "32019R0947"},
                            "date": {"value": "2019-05-24"},
                        },
                    ]
                }
            }

            from eurlxp.sparql import get_documents

            result = get_documents(types=["REG"], limit=1)
            assert len(result) == 1
            assert result[0]["celex"] == "32019R0947"
            assert result[0]["type"] == "REG"

    def test_get_documents_default_types(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_documents

            result = get_documents()
            assert result == []
            # Verify REG is in the query
            call_args = mock_run.call_args[0][0]
            assert "REG" in call_args
