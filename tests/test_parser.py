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

    def test_parse_metadata_propagation_per_article(self) -> None:
        """Regression: article/group/section must reflect position, not final values."""
        html = """<html><body>
            <p class="doc-ti">TEST REGULATION</p>
            <p class="ti-section-1">GENERAL PROVISIONS</p>
            <p class="ti-grseq-1">Chapter I Scope</p>
            <p class="ti-art">Article 1</p>
            <p class="normal">(1) First article first paragraph.</p>
            <p class="normal">(2) First article second paragraph.</p>
            <p class="ti-art">Article 2</p>
            <p class="normal">(1) Second article first paragraph.</p>
            <p class="ti-section-2">FINAL PROVISIONS</p>
            <p class="ti-grseq-2">Chapter II Entry into force</p>
            <p class="ti-art">Article 3</p>
            <p class="normal">(1) Third article first paragraph.</p>
        </body></html>"""
        df = parse_html(html)
        assert len(df) == 4

        # Article 1 rows
        assert df.iloc[0]["article"] == "1"
        assert df.iloc[0]["section"] == "GENERAL PROVISIONS"
        assert df.iloc[0]["group"] == "Chapter I Scope"
        assert df.iloc[0]["paragraph"] == "1"
        assert df.iloc[1]["article"] == "1"
        assert df.iloc[1]["paragraph"] == "2"

        # Article 2 row
        assert df.iloc[2]["article"] == "2"
        assert df.iloc[2]["section"] == "GENERAL PROVISIONS"
        assert df.iloc[2]["group"] == "Chapter I Scope"
        assert df.iloc[2]["paragraph"] == "1"

        # Article 3 row (different section and group)
        assert df.iloc[3]["article"] == "3"
        assert df.iloc[3]["section"] == "FINAL PROVISIONS"
        assert df.iloc[3]["group"] == "Chapter II Entry into force"
        assert df.iloc[3]["paragraph"] == "1"

    def test_preamble_has_no_article(self) -> None:
        """Preamble text before any article should not have article metadata."""
        html = """<html><body>
            <p class="doc-ti">TEST REGULATION</p>
            <p class="normal">THE EUROPEAN PARLIAMENT AND THE COUNCIL,</p>
            <p class="normal">Having regard to the Treaty,</p>
            <p class="ti-art">Article 1</p>
            <p class="normal">(1) Article content.</p>
        </body></html>"""
        df = parse_html(html)
        assert len(df) == 3

        # Preamble rows should have no article
        assert df.iloc[0]["article"] is None
        assert df.iloc[1]["article"] is None

        # Article 1 row should have article
        assert df.iloc[2]["article"] == "1"


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
