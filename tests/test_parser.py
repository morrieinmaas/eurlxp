"""Tests for the parser module."""

import pytest

from eurlxp.parser import (
    get_celex_id,
    get_possible_celex_ids,
    parse_article_paragraphs,
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
