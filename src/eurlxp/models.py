"""Pydantic models for EUR-Lex document parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    """EUR-Lex document types."""

    REGULATION = "R"
    DIRECTIVE = "L"
    DECISION = "D"
    RECOMMENDATION = "H"
    OPINION = "A"
    REGULATION_IMPL = "REG_IMPL"
    REGULATION_DEL = "REG_DEL"
    DIRECTIVE_IMPL = "DIR_IMPL"
    DIRECTIVE_DEL = "DIR_DEL"


class SectorId(str, Enum):
    """EUR-Lex sector identifiers."""

    TREATIES = "1"
    INTERNATIONAL_AGREEMENTS = "2"
    LEGISLATION = "3"
    COMPLEMENTARY_LEGISLATION = "4"
    PREPARATORY_ACTS = "5"
    CASE_LAW = "6"
    NATIONAL_TRANSPOSITION = "7"
    REFERENCES = "8"
    PARLIAMENTARY_QUESTIONS = "9"
    CONSOLIDATED_ACTS = "0"
    CORRIGENDA = "C"
    EFTA = "E"


class ParsedItem(BaseModel):
    """A single parsed item from an EUR-Lex document."""

    model_config = ConfigDict(frozen=True)

    text: str
    item_type: str = Field(alias="type")
    ref: list[str] = Field(default_factory=list)
    modifier: str | None = None
    document: str | None = None
    article: str | None = None
    article_subtitle: str | None = None
    paragraph: str | None = None
    group: str | None = None
    section: str | None = None


class DocumentMetadata(BaseModel):
    """Metadata for an EUR-Lex document."""

    model_config = ConfigDict(frozen=True)

    celex_id: str
    title: str | None = None
    document_type: str | None = None
    date_document: date | None = None
    date_publication: date | None = None
    language: str = "en"


class DocumentInfo(BaseModel):
    """Document information from SPARQL query."""

    model_config = ConfigDict(frozen=True)

    celex: str
    date: str | None = None
    link: str | None = None
    doc_type: str = Field(alias="type")


@dataclass
class ParseContext:
    """Mutable context during parsing."""

    document: str | None = None
    article: str | None = None
    article_subtitle: str | None = None
    paragraph: str | None = None
    group: str | None = None
    section: str | None = None

    def copy(self) -> ParseContext:
        """Create a shallow copy of the context."""
        return ParseContext(
            document=self.document,
            article=self.article,
            article_subtitle=self.article_subtitle,
            paragraph=self.paragraph,
            group=self.group,
            section=self.section,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with all fields (None values included for consistent columns)."""
        return {
            "document": self.document,
            "article": self.article,
            "paragraph": self.paragraph,
            "group": self.group,
            "section": self.section,
        }


@dataclass
class ParseResult:
    """Result of parsing a single element."""

    text: str
    item_type: str
    ref: list[str] = field(default_factory=list)
    modifier: str | None = None
    context: ParseContext = field(default_factory=ParseContext)

    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dictionary for DataFrame creation."""
        result: dict[str, Any] = {
            "text": self.text,
            "type": self.item_type,
            "ref": self.ref,
        }
        if self.modifier:
            result["modifier"] = self.modifier
        result.update(self.context.to_dict())
        return result


# RDF/SPARQL prefixes used by EUR-Lex
EURLEX_PREFIXES: dict[str, str] = {
    "cdm": "http://publications.europa.eu/ontology/cdm#",
    "celex": "http://publications.europa.eu/resource/celex/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "cellar": "http://publications.europa.eu/resource/cellar/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
}
