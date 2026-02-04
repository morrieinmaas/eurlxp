"""Tests for the parser module."""

from eurlxp.parser import (
    get_celex_id,
    get_possible_celex_ids,
    is_valid_celex_id,
    parse_article_paragraphs,
    parse_celex_id,
    parse_html,
)


class TestCelexId:
    """Tests for CELEX ID functions."""

    def test_get_celex_id_year_first(self) -> None:
        assert get_celex_id("2019/947") == "32019R0947"

    def test_get_celex_id_year_second(self) -> None:
        assert get_celex_id("947/2019") == "32019R0947"

    def test_get_celex_id_with_document_type(self) -> None:
        assert get_celex_id("2019/947", document_type="L") == "32019L0947"

    def test_get_celex_id_with_sector(self) -> None:
        assert get_celex_id("2019/947", sector_id="5") == "52019R0947"

    def test_get_possible_celex_ids_contains_expected(self) -> None:
        possible = get_possible_celex_ids("2019/947")
        assert "32019R0947" in possible

    def test_get_possible_celex_ids_with_type(self) -> None:
        possible = get_possible_celex_ids("2019/947", document_type="R")
        assert all("R" in cid for cid in possible)


class TestParseArticleParagraphs:
    """Tests for article paragraph parsing."""

    def test_numbered_paragraphs(self) -> None:
        result = parse_article_paragraphs("Intro:     1. First     2. Second")
        assert result == {None: "Intro:", "1.": "First", "2.": "Second"}

    def test_parenthesized_paragraphs(self) -> None:
        result = parse_article_paragraphs("Intro:     (1) First     (2) Second")
        assert result == {None: "Intro:", "(1)": "First", "(2)": "Second"}

    def test_single_paragraph(self) -> None:
        result = parse_article_paragraphs("Just some text")
        assert result == {None: "Just some text"}


class TestParseHtml:
    """Tests for HTML parsing."""

    def test_parse_simple_html(self) -> None:
        html = '<html><body><p class="normal">Text</p></body></html>'
        df = parse_html(html)
        assert len(df) == 1
        assert df.iloc[0]["text"] == "Text"
        assert df.iloc[0]["type"] == "text"

    def test_parse_invalid_html(self) -> None:
        df = parse_html("<html")
        assert len(df) == 0

    def test_parse_empty_html(self) -> None:
        df = parse_html("<html></html>")
        assert len(df) == 0

    def test_parse_with_document_title(self) -> None:
        html = """<html><body>
            <p class="doc-ti">REGULATION</p>
            <p class="normal">Content text</p>
        </body></html>"""
        df = parse_html(html)
        assert len(df) == 1
        assert df.iloc[0]["document"] == "REGULATION"

    def test_parse_with_article(self) -> None:
        html = """<html><body>
            <p class="ti-art">Article 1</p>
            <p class="normal">Article content</p>
        </body></html>"""
        df = parse_html(html)
        assert len(df) == 1
        assert df.iloc[0]["article"] == "1"

    def test_parse_with_group(self) -> None:
        html = """<html><body>
            <p class="ti-grseq-1">Group Title</p>
            <p class="normal">Group content</p>
        </body></html>"""
        df = parse_html(html)
        assert len(df) == 1
        assert df.iloc[0]["group"] == "Group Title"

    def test_parse_numbered_paragraph(self) -> None:
        html = '<html><body><p class="normal">1. First paragraph</p></body></html>'
        df = parse_html(html)
        assert len(df) == 1
        assert df.iloc[0]["paragraph"] == "1"
        assert df.iloc[0]["text"] == "First paragraph"


class TestParseCelexId:
    """Tests for CELEX ID parsing and validation."""

    def test_parse_standard_celex_id(self) -> None:
        result = parse_celex_id("32019R0947")
        assert result is not None
        assert result["sector"] == "3"
        assert result["year"] == "2019"
        assert result["doc_type"] == "R"
        assert result["number"] == "0947"
        assert result["suffix"] is None

    def test_parse_celex_id_with_suffix(self) -> None:
        result = parse_celex_id("32012L0029R(06)")
        assert result is not None
        assert result["sector"] == "3"
        assert result["year"] == "2012"
        assert result["doc_type"] == "L"
        assert result["number"] == "0029"
        assert result["suffix"] == "R(06)"

    def test_parse_celex_id_sector_5(self) -> None:
        result = parse_celex_id("52026XG00745")
        assert result is not None
        assert result["sector"] == "5"
        assert result["year"] == "2026"
        assert result["doc_type"] == "XG"
        assert result["number"] == "00745"

    def test_parse_celex_id_budget_type(self) -> None:
        result = parse_celex_id("32026B00249")
        assert result is not None
        assert result["sector"] == "3"
        assert result["doc_type"] == "B"

    def test_parse_oj_reference_returns_none(self) -> None:
        """OJ series references like C/2026/00064 are not CELEX IDs."""
        result = parse_celex_id("C/2026/00064")
        assert result is None

    def test_parse_empty_string_returns_none(self) -> None:
        result = parse_celex_id("")
        assert result is None

    def test_parse_invalid_format_returns_none(self) -> None:
        result = parse_celex_id("not-a-celex-id")
        assert result is None

    def test_parse_celex_id_invalid_year_returns_none(self) -> None:
        result = parse_celex_id("31800R0001")  # Year too old
        assert result is None


class TestIsValidCelexId:
    """Tests for CELEX ID validation."""

    def test_valid_celex_ids(self) -> None:
        assert is_valid_celex_id("32019R0947") is True
        assert is_valid_celex_id("32012L0029R(06)") is True
        assert is_valid_celex_id("52026XG00745") is True
        assert is_valid_celex_id("32026B00249") is True

    def test_invalid_celex_ids(self) -> None:
        assert is_valid_celex_id("C/2026/00064") is False  # OJ reference
        assert is_valid_celex_id("") is False
        assert is_valid_celex_id("invalid") is False
