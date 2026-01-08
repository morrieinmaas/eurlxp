"""Tests for the models module."""

from eurlxp.models import (
    DocumentType,
    EURLEX_PREFIXES,
    ParseContext,
    ParseResult,
    SectorId,
)


class TestDocumentType:
    """Tests for DocumentType enum."""

    def test_regulation(self) -> None:
        assert DocumentType.REGULATION.value == "R"

    def test_directive(self) -> None:
        assert DocumentType.DIRECTIVE.value == "L"


class TestSectorId:
    """Tests for SectorId enum."""

    def test_legislation(self) -> None:
        assert SectorId.LEGISLATION.value == "3"

    def test_treaties(self) -> None:
        assert SectorId.TREATIES.value == "1"


class TestParseContext:
    """Tests for ParseContext dataclass."""

    def test_copy(self) -> None:
        ctx = ParseContext(document="Doc", article="1")
        copy = ctx.copy()
        assert copy.document == "Doc"
        assert copy.article == "1"
        copy.article = "2"
        assert ctx.article == "1"  # Original unchanged

    def test_to_dict(self) -> None:
        ctx = ParseContext(document="Doc", article="1")
        d = ctx.to_dict()
        assert d == {"document": "Doc", "article": "1"}
        assert "paragraph" not in d  # None values excluded


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_to_dict(self) -> None:
        ctx = ParseContext(document="Doc")
        result = ParseResult(text="Hello", item_type="text", context=ctx)
        d = result.to_dict()
        assert d["text"] == "Hello"
        assert d["type"] == "text"
        assert d["document"] == "Doc"
        assert "modifier" not in d

    def test_to_dict_with_modifier(self) -> None:
        result = ParseResult(text="Hello", item_type="text", modifier="italic")
        d = result.to_dict()
        assert d["modifier"] == "italic"


class TestPrefixes:
    """Tests for EURLEX_PREFIXES constant."""

    def test_contains_cdm(self) -> None:
        assert "cdm" in EURLEX_PREFIXES
        assert EURLEX_PREFIXES["cdm"].startswith("http://")

    def test_contains_celex(self) -> None:
        assert "celex" in EURLEX_PREFIXES
