"""HTML parser for EUR-Lex documents."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from eurlxp.models import ParseContext, ParseResult

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

# XML namespaces used in EUR-Lex documents
XHTML_NAMESPACE = {"html": "http://www.w3.org/1999/xhtml"}


def _get_tag_name(raw_tag_name: str) -> str:
    """Extract tag name from potentially namespaced tag.

    Examples
    --------
    >>> _get_tag_name('tag}test')
    'test'
    >>> _get_tag_name('div')
    'div'
    """
    return raw_tag_name.split("}")[1] if "}" in raw_tag_name else raw_tag_name


def _get_text(element: Element) -> str:
    """Extract text content from an element, handling nested elements.

    Examples
    --------
    >>> _get_text(ETree.fromstring('<p>Text</p>'))
    'Text'
    >>> _get_text(ETree.fromstring('<p><span>Text</span></p>'))
    'Text'
    """
    if len(element) == 1:
        return _get_text(element[0])
    return (element.text or "").strip()


def _parse_modifiers(element: Element, ref: list[str], context: ParseContext) -> list[ParseResult]:
    """Parse elements with modifier classes (italic, signatory, note)."""
    css_class = element.attrib.get("class", "")
    text = _get_text(element)

    modifier_classes = {"italic", "signatory", "note"}
    if css_class in modifier_classes:
        return [ParseResult(text=text, item_type="text", ref=ref.copy(), modifier=css_class, context=context.copy())]
    return []


def _parse_span(element: Element, ref: list[str], context: ParseContext) -> list[ParseResult]:
    """Parse a <span> or <p> tag based on its class.

    Supports both old EUR-Lex classes (doc-ti, normal, ti-art) and
    new OJ format classes (oj-doc-ti, oj-normal, oj-ti-art).

    Examples
    --------
    >>> _parse_span(ETree.fromstring('<p class="doc-ti">Text</p>'), [], ParseContext())
    [ParseResult(text='Text', item_type='doc-title', ...)]
    >>> _parse_span(ETree.fromstring('<p class="oj-doc-ti">Text</p>'), [], ParseContext())
    [ParseResult(text='Text', item_type='doc-title', ...)]
    """
    results: list[ParseResult] = []
    css_class = element.attrib.get("class", "")

    if not css_class:
        return results

    text = _get_text(element)

    # Normalize class name: strip "oj-" prefix if present for matching
    normalized_class = css_class[3:] if css_class.startswith("oj-") else css_class

    # Document title classes: OJ format (doc-ti) and Commission format (Titreobjet, Typedudocument)
    if normalized_class in ("doc-ti", "Titreobjet", "Typedudocument"):
        if context.document is None:
            context.document = ""
        context.document += text
        results.append(ParseResult(text=text, item_type="doc-title", ref=ref.copy(), context=context.copy()))

    elif normalized_class == "sti-art":
        context.article_subtitle = text
        results.append(ParseResult(text=text, item_type="art-subtitle", ref=ref.copy(), context=context.copy()))

    # Article title classes: OJ format (ti-art) and Commission format (Titrearticle)
    elif normalized_class in ("ti-art", "Titrearticle"):
        context.article = text.replace("Article", "").strip()
        results.append(ParseResult(text=text, item_type="art-title", ref=ref.copy(), context=context.copy()))

    elif normalized_class.startswith("ti-grseq-"):
        results.append(ParseResult(text=text, item_type="group-title", ref=ref.copy(), context=context.copy()))
        context.group = text

    elif normalized_class.startswith("ti-section-"):
        results.append(ParseResult(text=text, item_type="section-title", ref=ref.copy(), context=context.copy()))
        context.section = text

    # Normal text classes: OJ format (normal) and Commission format (Normal - capital N)
    elif normalized_class in ("normal", "Normal"):
        match = re.match(r"^([0-9]+)[.]", text)
        if match:
            context.paragraph = text.split(".")[0]
            text = ".".join(text.split(".")[1:]).strip()
        results.append(ParseResult(text=text, item_type="text", ref=ref.copy(), context=context.copy()))

    else:
        results.extend(_parse_modifiers(element, ref, context))

    return results


def _parse_article(
    tree: Element, ref: list[str] | None = None, context: ParseContext | None = None
) -> list[ParseResult]:
    """Recursively parse an article/document tree.

    Examples
    --------
    >>> _parse_article(ETree.fromstring('<html><a>Link</a></html>'))
    [ParseResult(text='Link', item_type='link', ...)]
    """
    ref = ref if ref is not None else []
    context = context if context is not None else ParseContext()
    results: list[ParseResult] = []
    new_context = context.copy()

    for child in tree:
        tag_name = _get_tag_name(child.tag)

        if tag_name == "a":
            results.append(
                ParseResult(text=_get_text(child), item_type="link", ref=ref.copy(), context=new_context.copy())
            )

        elif tag_name in ("p", "span"):
            results.extend(_parse_span(child, ref, new_context))

        elif tag_name == "table":
            # Handle two-column tables with reference in first column
            td_elements = child.findall("html:tbody/html:tr/html:td", namespaces=XHTML_NAMESPACE) + child.findall(
                "tbody/tr/td"
            )
            if len(td_elements) == 2 and len(td_elements[0]) == 1 and _get_tag_name(td_elements[0][0].tag) == "p":
                key = _get_text(td_elements[0][0])
                results.extend(_parse_article(td_elements[1], ref + [key], new_context))

        elif tag_name == "div":
            results.extend(_parse_article(child, ref, new_context))

        elif tag_name == "body":
            results.extend(_parse_article(child, ref, context))

        # Skip head, hr, and other non-content elements

    return results


def parse_html(html: str) -> pd.DataFrame:
    """Parse EUR-Lex HTML into a pandas DataFrame.

    Parameters
    ----------
    html : str
        The HTML content to parse.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: text, type, ref, and context fields
        (document, article, article_subtitle, paragraph, group, section).

    Examples
    --------
    >>> parse_html('<html><body><p class="normal">Text</p></body></html>').to_dict(orient='records')
    [{'text': 'Text', 'type': 'text', 'ref': [], ...}]
    >>> parse_html('<html').to_dict(orient='records')
    []
    """
    # Use BeautifulSoup for robust parsing of all EUR-Lex formats
    # (OJ format, Commission proposals, etc.)
    results = _parse_html_with_beautifulsoup(html)

    records = [r.to_dict() for r in results]

    df = pd.DataFrame.from_records(records) if records else pd.DataFrame()

    # Filter to only text items (matching original behavior)
    if "type" in df.columns:
        df = df[df["type"] == "text"].copy()

    return df  # type: ignore[return-value]


def _parse_html_with_beautifulsoup(html: str) -> list[ParseResult]:
    """Parse HTML/XML using BeautifulSoup.

    Tries lxml-xml parser first (for XHTML documents), then falls back to
    lxml HTML parser for older HTML documents.
    """
    from bs4 import BeautifulSoup

    # Try lxml-xml parser first (for XHTML documents)
    soup = BeautifulSoup(html, "lxml-xml")

    # If no <p> tags found, try lxml HTML parser (for older HTML documents)
    if not soup.find_all("p"):
        soup = BeautifulSoup(html, "lxml")

    results: list[ParseResult] = []
    context = ParseContext()

    # Find document title
    # Supports: OJ format (doc-ti, oj-doc-ti), Commission format (Titreobjet, Typedudocument)
    for doc_ti in soup.find_all("p", class_=["doc-ti", "oj-doc-ti", "Titreobjet", "Typedudocument"]):
        text = doc_ti.get_text(strip=True)
        if text:
            if context.document is None:
                context.document = ""
            context.document += text
            results.append(ParseResult(text=text, item_type="doc-title", ref=[], context=context.copy()))

    # Find article titles
    # Supports: OJ format (ti-art, oj-ti-art), Commission format (Titrearticle)
    for ti_art in soup.find_all("p", class_=["ti-art", "oj-ti-art", "Titrearticle"]):
        text = ti_art.get_text(strip=True)
        if text:
            context.article = text.replace("Article", "").strip()
            results.append(ParseResult(text=text, item_type="art-title", ref=[], context=context.copy()))

    # Find group titles (ti-grseq-* classes)
    for p_tag in soup.find_all("p"):
        css_class = p_tag.get("class")
        if css_class is None:
            css_class = ""
        elif isinstance(css_class, list):
            css_class = " ".join(css_class)
        if css_class and ("ti-grseq-" in css_class or "oj-ti-grseq-" in css_class):
            text = p_tag.get_text(strip=True)
            if text:
                context.group = text
                results.append(ParseResult(text=text, item_type="group-title", ref=[], context=context.copy()))

    # Find section titles (ti-section-* classes)
    for p_tag in soup.find_all("p"):
        css_class = p_tag.get("class")
        if css_class is None:
            css_class = ""
        elif isinstance(css_class, list):
            css_class = " ".join(css_class)
        if css_class and ("ti-section-" in css_class or "oj-ti-section-" in css_class):
            text = p_tag.get_text(strip=True)
            if text:
                context.section = text
                results.append(ParseResult(text=text, item_type="section-title", ref=[], context=context.copy()))

    # Find normal text paragraphs
    # Supports: OJ format (normal, oj-normal), Commission format (Normal - capital N)
    for normal in soup.find_all("p", class_=["normal", "oj-normal", "Normal"]):
        text = normal.get_text(strip=True)
        if text:
            # Check for numbered paragraphs
            match = re.match(r"^[(]?([0-9]+)[).]?", text)
            if match:
                context.paragraph = match.group(1)
                # Remove the number prefix
                text = re.sub(r"^[(]?[0-9]+[).]?\s*", "", text)
            results.append(ParseResult(text=text, item_type="text", ref=[], context=context.copy()))

    # Fallback: if no text results found, extract text from all <p> tags
    # This handles unknown EUR-Lex formats that use different CSS classes
    text_results = [r for r in results if r.item_type == "text"]
    if not text_results:
        for p_tag in soup.find_all("p"):
            text = p_tag.get_text(strip=True)
            # Skip short text, HTML fragments, and navigation elements
            if (
                text
                and len(text) > 30
                and not text.startswith("role=")
                and "aria-label" not in text
                and "<" not in text
            ):
                results.append(ParseResult(text=text, item_type="text", ref=[], context=context.copy()))

    return results


def parse_article_paragraphs(article: str) -> dict[str | None, str]:
    """Convert an article text to paragraphs.

    Parameters
    ----------
    article : str
        The article text to parse.

    Returns
    -------
    dict[str | None, str]
        Mapping from paragraph identifier to paragraph text.

    Examples
    --------
    >>> parse_article_paragraphs("Intro:     1. First     2. Second")
    {None: 'Intro:', '1.': 'First', '2.': 'Second'}
    >>> parse_article_paragraphs("Intro:     (1) First     (2) Second")
    {None: 'Intro:', '(1)': 'First', '(2)': 'Second'}
    """
    paragraphs: dict[str | None, list[str]] = {}
    paragraph: str | None = None
    article = article.replace("     ", "\n")

    for line in article.split("\n"):
        # Check for numbered paragraph (e.g., "1.")
        match = re.match(r"^([0-9]+)[.]", line)
        if match:
            paragraph = match.group(0)
            line = ".".join(line.split(".")[1:]).strip()
        else:
            # Check for parenthesized paragraph (e.g., "(1)")
            match = re.match(r"^[(]([0-9]+)[)]", line)
            if match:
                paragraph = match.group(0)
                line = ")".join(line.split(")")[1:]).strip()

        if paragraph not in paragraphs:
            paragraphs[paragraph] = []
        paragraphs[paragraph].append(line)

    return {p: "\n".join(lines).strip() for p, lines in paragraphs.items()}


def parse_celex_id(celex_id: str) -> dict[str, str | None] | None:
    """Parse a CELEX ID into its components.

    Parameters
    ----------
    celex_id : str
        The CELEX identifier to parse.

    Returns
    -------
    dict[str, str | None] | None
        A dict with keys: sector, year, doc_type, number, suffix.
        Returns None if the ID is not a valid CELEX format.

    Examples
    --------
    >>> parse_celex_id('32019R0947')
    {'sector': '3', 'year': '2019', 'doc_type': 'R', 'number': '0947', 'suffix': None}
    >>> parse_celex_id('32012L0029R(06)')
    {'sector': '3', 'year': '2012', 'doc_type': 'L', 'number': '0029', 'suffix': 'R(06)'}
    >>> parse_celex_id('C/2026/00064')  # OJ reference, not CELEX
    """
    if not celex_id:
        return None

    # OJ series references like C/2026/00064 are not CELEX IDs
    if "/" in celex_id:
        return None

    # CELEX format: [Sector][Year (4 digits)][Type (1-2 chars)][Number (2-5 digits)][Optional suffix]
    # Sectors: 0-9, C, E
    # Example: 32019R0947, 52026XG00745, 32012L0029R(06)
    pattern = r"^([0-9CE])(\d{4})([A-Z]{1,3})(\d{2,5})(.*)$"
    match = re.match(pattern, celex_id)

    if not match:
        return None

    sector, year, doc_type, number, suffix = match.groups()

    # Validate year is reasonable (1950-2100)
    year_int = int(year)
    if year_int < 1950 or year_int > 2100:
        return None

    return {
        "sector": sector,
        "year": year,
        "doc_type": doc_type,
        "number": number,
        "suffix": suffix if suffix else None,
    }


def is_valid_celex_id(celex_id: str) -> bool:
    """Check if a string is a valid CELEX ID format.

    Parameters
    ----------
    celex_id : str
        The string to check.

    Returns
    -------
    bool
        True if the string matches CELEX ID format.

    Examples
    --------
    >>> is_valid_celex_id('32019R0947')
    True
    >>> is_valid_celex_id('C/2026/00064')
    False
    """
    return parse_celex_id(celex_id) is not None


def get_celex_id(slash_notation: str, document_type: str = "R", sector_id: str = "3") -> str:
    """Derive CELEX ID from slash notation (e.g., 2019/947).

    Parameters
    ----------
    slash_notation : str
        Document reference in slash notation (e.g., "2019/947" or "947/2019").
    document_type : str
        Document type code (default: "R" for regulation).
    sector_id : str
        Sector identifier (default: "3" for legislation).

    Returns
    -------
    str
        The CELEX ID.

    Examples
    --------
    >>> get_celex_id('2019/947')
    '32019R0947'
    >>> get_celex_id('947/2019')
    '32019R0947'

    Changelog 04-02-2026
    --------
    Handle cases where both are years - like 2025/1987, using the ruling that the first term is year

    """
    term1_str, term2_str = slash_notation.split("/")
    current_year = datetime.now().year
    term1, term2 = int(term1_str), int(term2_str)

    term1_is_year = 1800 <= term1 <= current_year
    term2_is_year = 1800 <= term2 <= current_year

    year, document_id = term1, term2
    if term1_is_year and not term2_is_year:
        year, document_id = term1, term2
    elif term2_is_year and not term1_is_year:
        year, document_id = term2, term1

    return f"{sector_id}{year}{document_type}{str(document_id).zfill(4)}"


def get_possible_celex_ids(
    slash_notation: str,
    document_type: str | None = None,
    sector_id: str | None = None,
) -> list[str]:
    """Get list of possible CELEX IDs for a slash notation.

    Parameters
    ----------
    slash_notation : str
        Document reference in slash notation.
    document_type : str | None
        Document type code (if None, tries all common types).
    sector_id : str | None
        Sector identifier (if None, tries all sectors).

    Returns
    -------
    list[str]
        List of possible CELEX IDs.

    Examples
    --------
    >>> '32019R0947' in get_possible_celex_ids("2019/947")
    True

    Changelog - 04-02-2026
    --------
    Add D, to possible document types later removed E due to query character limit
    """
    sector_ids = [str(i) for i in range(10)] + ["C", "E"] if sector_id is None else [str(sector_id)]
    document_types = (
        ["L", "R", "D", "PC", "DC", "SC", "JC", "CJ", "CC", "CO"] if document_type is None else [document_type]
    )

    # document_types = (
    #     ["L", "R", "E", "D", "PC", "DC", "SC", "SWD", "JC", "CJ", "CC", "CO"] if document_type is None else [document_type]
    # )

    return [get_celex_id(slash_notation, dt, sid) for sid in sector_ids for dt in document_types]


def process_paragraphs(paragraphs: list[dict]) -> pd.DataFrame:
    """Process and filter paragraphs, removing boilerplate text.

    Parameters
    ----------
    paragraphs : list[dict]
        List of paragraph dictionaries with 'paragraph' key.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame of paragraphs.

    Examples
    --------
    >>> process_paragraphs([]).to_dict(orient='records')
    []
    >>> process_paragraphs([{'celex_id': '1', 'paragraph': 'Done at 2021-11-25.'}]).to_dict(orient='records')
    []
    """
    df: pd.DataFrame = pd.DataFrame.from_records(paragraphs)

    if "paragraph" not in df.columns or len(df) == 0:
        return df

    para_col: pd.Series[str] = df["paragraph"]  # type: ignore[assignment]

    # Filter patterns to exclude
    exclusion_starts = ["Done at", "It shall apply from"]
    exclusion_contains = ["is replaced by", "is amended ", "is repealed with", "'", "'"]
    exclusion_ends = [
        "is updated.",
        "is deleted.",
        "is removed.",
        "is hereby repealed.",
        "are updated.",
        "are deleted.",
        "are removed.",
    ]

    for pattern in exclusion_starts:
        if len(df) > 0:
            mask = para_col.str.startswith(pattern)
            df = df[~mask].copy()  # type: ignore[assignment]
            para_col = df["paragraph"]  # type: ignore[assignment]

    for pattern in exclusion_contains:
        if len(df) > 0:
            mask = para_col.str.contains(pattern, regex=False)
            df = df[~mask].copy()  # type: ignore[assignment]
            para_col = df["paragraph"]  # type: ignore[assignment]

    for pattern in exclusion_ends:
        if len(df) > 0:
            mask = para_col.str.endswith(pattern)
            df = df[~mask].copy()  # type: ignore[assignment]
            para_col = df["paragraph"]  # type: ignore[assignment]

    # Inclusion filters
    if len(df) > 0:
        mask = para_col.str.endswith(".")
        df = df[mask].copy()  # type: ignore[assignment]
        para_col = df["paragraph"]  # type: ignore[assignment]
    if len(df) > 0:
        mask = para_col.apply(lambda t: len(t) > 0 and t[0].isupper())
        df = df[mask].copy()  # type: ignore[assignment]
        para_col = df["paragraph"]  # type: ignore[assignment]
    if len(df) > 0:
        mask = para_col.str.len() >= 100
        df = df[mask].copy()  # type: ignore[assignment]
    if len(df) > 0:
        df = df.drop_duplicates(subset="paragraph")

    return df
