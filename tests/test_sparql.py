"""Tests for the SPARQL module."""

from unittest.mock import MagicMock, patch

import pytest

from eurlxp.sparql import DateType, DocumentReference, convert_sparql_output_to_dataframe


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

        # Mock the exceptions submodule
        mock_exceptions = MagicMock()
        mock_exceptions.EndPointInternalError = Exception
        mock_exceptions.EndPointNotFound = Exception
        mock_exceptions.QueryBadFormed = Exception

        with (
            patch("eurlxp.sparql._check_sparql_dependencies"),
            patch.dict(
                "sys.modules",
                {
                    "SPARQLWrapper": mock_sparql_module,
                    "SPARQLWrapper.SPARQLExceptions": mock_exceptions,
                },
            ),
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


class TestDocumentReference:
    """Tests for DocumentReference dataclass."""

    def test_document_reference_creation(self) -> None:
        doc = DocumentReference(
            cellar_url="http://publications.europa.eu/resource/cellar/abc123",
            celex_id="32019R0947",
            raw_id="32019R0947",
            document_date="2019-05-24",
        )
        assert doc.cellar_url == "http://publications.europa.eu/resource/cellar/abc123"
        assert doc.celex_id == "32019R0947"
        assert doc.raw_id == "32019R0947"
        assert doc.document_date == "2019-05-24"

    def test_document_reference_with_none_celex(self) -> None:
        doc = DocumentReference(
            cellar_url="http://publications.europa.eu/resource/cellar/abc123",
            celex_id=None,
            raw_id="C/2026/00064",
            document_date="2026-01-15",
        )
        assert doc.celex_id is None
        assert doc.raw_id == "C/2026/00064"


class TestGetIdsAndUrlsViaDate:
    """Tests for get_ids_and_urls_via_date."""

    def test_get_ids_and_urls_via_date_mocked(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {
                            "work": {"value": "http://publications.europa.eu/resource/cellar/abc123"},
                            "celexId": {"value": "32019R0947"},
                            "targetDate": {"value": "2019-05-24"},
                        },
                        {
                            "work": {"value": "http://publications.europa.eu/resource/cellar/def456"},
                            "celexId": {"value": "C/2026/00064"},
                            "targetDate": {"value": "2026-01-15"},
                        },
                    ]
                }
            }

            from eurlxp.sparql import get_ids_and_urls_via_date

            result = get_ids_and_urls_via_date("2026-01-15")

            assert len(result) == 2

            # First document has valid CELEX ID
            assert result[0].cellar_url == "http://publications.europa.eu/resource/cellar/abc123"
            assert result[0].celex_id == "32019R0947"
            assert result[0].raw_id == "32019R0947"

            # Second document has OJ reference (not valid CELEX)
            assert result[1].cellar_url == "http://publications.europa.eu/resource/cellar/def456"
            assert result[1].celex_id is None  # Invalid CELEX format
            assert result[1].raw_id == "C/2026/00064"

    def test_get_ids_and_urls_via_date_single_day(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_ids_and_urls_via_date

            get_ids_and_urls_via_date("2026-01-15")

            # Verify query uses same date for both from and to
            call_args = mock_run.call_args[0][0]
            assert "2026-01-15" in call_args

    def test_get_ids_and_urls_via_date_range(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_ids_and_urls_via_date

            get_ids_and_urls_via_date("2026-01-15", "2026-01-20")

            call_args = mock_run.call_args[0][0]
            assert "2026-01-15" in call_args
            assert "2026-01-20" in call_args

    def test_get_ids_and_urls_validates_celex_with_suffix(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {
                            "work": {"value": "http://publications.europa.eu/resource/cellar/xyz789"},
                            "celexId": {"value": "32012L0029R(06)"},
                            "targetDate": {"value": "2026-01-15"},
                        },
                    ]
                }
            }

            from eurlxp.sparql import get_ids_and_urls_via_date

            result = get_ids_and_urls_via_date("2026-01-15")

            # CELEX with suffix is still valid
            assert result[0].celex_id == "32012L0029R(06)"
            assert result[0].raw_id == "32012L0029R(06)"

    def test_get_ids_and_urls_via_date_with_date_type_modified(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_ids_and_urls_via_date

            get_ids_and_urls_via_date("2026-01-15", date_type=DateType.MODIFIED)

            # Verify query uses modification date predicate
            call_args = mock_run.call_args[0][0]
            assert "work_date_lastUpdate" in call_args

    def test_get_ids_and_urls_via_date_with_date_type_string(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_ids_and_urls_via_date

            # Test that string "modified" works as well as DateType.MODIFIED
            get_ids_and_urls_via_date("2026-01-15", date_type="modified")

            call_args = mock_run.call_args[0][0]
            assert "work_date_lastUpdate" in call_args

    def test_get_ids_and_urls_via_date_with_date_type_created(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import get_ids_and_urls_via_date

            get_ids_and_urls_via_date("2026-01-15", date_type=DateType.CREATED)

            call_args = mock_run.call_args[0][0]
            assert "work_date_creation" in call_args

    @pytest.mark.integration
    def test_get_ids_and_urls_via_date_integration(self) -> None:
        try:
            from eurlxp.sparql import get_ids_and_urls_via_date

            result = get_ids_and_urls_via_date("2024-01-15")
            # Should return a list (may be empty depending on date)
            assert isinstance(result, list)
            if result:
                # Verify structure of returned items
                assert hasattr(result[0], "cellar_url")
                assert hasattr(result[0], "celex_id")
                assert hasattr(result[0], "raw_id")
                assert hasattr(result[0], "document_date")
        except ImportError:
            pytest.skip("SPARQL dependencies not installed")


class TestLookupCellarUrl:
    """Tests for lookup_cellar_url function."""

    def test_lookup_cellar_url_found(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {
                "results": {
                    "bindings": [
                        {"work": {"value": "http://publications.europa.eu/resource/cellar/abc123"}},
                    ]
                }
            }

            from eurlxp.sparql import lookup_cellar_url

            result = lookup_cellar_url("C/2026/00064")
            assert result == "http://publications.europa.eu/resource/cellar/abc123"

    def test_lookup_cellar_url_not_found(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.return_value = {"results": {"bindings": []}}

            from eurlxp.sparql import lookup_cellar_url

            result = lookup_cellar_url("invalid-id-12345")
            assert result is None

    def test_lookup_cellar_url_handles_exception(self) -> None:
        with patch("eurlxp.sparql.run_query") as mock_run:
            mock_run.side_effect = Exception("SPARQL error")

            from eurlxp.sparql import lookup_cellar_url

            result = lookup_cellar_url("C/2026/00064")
            assert result is None

    @pytest.mark.integration
    def test_lookup_cellar_url_integration(self) -> None:
        try:
            from eurlxp.sparql import lookup_cellar_url

            # Look up a known CELEX ID
            result = lookup_cellar_url("32019R0947")
            # Should return a cellar URL or None (depending on SPARQL availability)
            if result:
                assert "publications.europa.eu" in result
        except ImportError:
            pytest.skip("SPARQL dependencies not installed")
