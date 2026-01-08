"""HTML parser for EUR-Lex documents."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ETree

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

    Examples
    --------
    >>> _parse_span(ETree.fromstring('<p class="doc-ti">Text</p>'), [], ParseContext())
    [ParseResult(text='Text', item_type='doc-title', ...)]
    """
    results: list[ParseResult] = []
    css_class = element.attrib.get("class", "")

    if not css_class:
        return results

    text = _get_text(element)

    if css_class == "doc-ti":
        if context.document is None:
            context.document = ""
        context.document += text
        results.append(ParseResult(text=text, item_type="doc-title", ref=ref.copy(), context=context.copy()))

    elif css_class == "sti-art":
        context.article_subtitle = text
        results.append(ParseResult(text=text, item_type="art-subtitle", ref=ref.copy(), context=context.copy()))

    elif css_class == "ti-art":
        context.article = text.replace("Article", "").strip()
        results.append(ParseResult(text=text, item_type="art-title", ref=ref.copy(), context=context.copy()))

    elif css_class.startswith("ti-grseq-"):
        results.append(ParseResult(text=text, item_type="group-title", ref=ref.copy(), context=context.copy()))
        context.group = text

    elif css_class.startswith("ti-section-"):
        results.append(ParseResult(text=text, item_type="section-title", ref=ref.copy(), context=context.copy()))
        context.section = text

    elif css_class == "normal":
        match = re.match(r"^([0-9]+)[.]", text)
        if match:
            context.paragraph = text.split(".")[0]
            text = ".".join(text.split(".")[1:]).strip()
        results.append(ParseResult(text=text, item_type="text", ref=ref.copy(), context=context.copy()))

    else:
        results.extend(_parse_modifiers(element, ref, context))

    return results


def _parse_article(tree: Element, ref: list[str] | None = None, context: ParseContext | None = None) -> list[ParseResult]:
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
    try:
        tree = ETree.fromstring(html)
    except ETree.ParseError:
        return pd.DataFrame()

    results = _parse_article(tree)
    records = [r.to_dict() for r in results]

    df = pd.DataFrame.from_records(records) if records else pd.DataFrame()

    # Filter to only text items (matching original behavior)
    if "type" in df.columns:
        df = df[df["type"] == "text"]

    return df


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
    """
    term1_str, term2_str = slash_notation.split("/")
    current_year = datetime.now().year
    term1, term2 = int(term1_str), int(term2_str)

    term1_is_year = 1800 <= term1 <= current_year
    term2_is_year = 1800 <= term2 <= current_year

    year, document_id = term2, term1
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
    """
    sector_ids = [str(i) for i in range(10)] + ["C", "E"] if sector_id is None else [str(sector_id)]
    document_types = (
        ["L", "R", "E", "PC", "DC", "SC", "JC", "CJ", "CC", "CO"] if document_type is None else [document_type]
    )

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
    df = pd.DataFrame.from_records(paragraphs)

    if "paragraph" not in df.columns or len(df) == 0:
        return df

    # Filter patterns to exclude
    exclusion_patterns = [
        (lambda s: s.str.startswith("Done at")),
        (lambda s: s.str.startswith("It shall apply from")),
        (lambda s: s.str.contains("is replaced by")),
        (lambda s: s.str.endswith("is updated.")),
        (lambda s: s.str.endswith("is deleted.")),
        (lambda s: s.str.endswith("is removed.")),
        (lambda s: s.str.endswith("is hereby repealed.")),
        (lambda s: s.str.endswith("are updated.")),
        (lambda s: s.str.endswith("are deleted.")),
        (lambda s: s.str.endswith("are removed.")),
        (lambda s: s.str.contains("is amended ")),
        (lambda s: s.str.contains("is repealed with")),
        (lambda s: s.str.contains("'")),
        (lambda s: s.str.contains("'")),
    ]

    for pattern in exclusion_patterns:
        if len(df) > 0:
            df = df[~pattern(df.paragraph)]

    # Inclusion filters
    if len(df) > 0:
        df = df[df.paragraph.str.endswith(".")]
    if len(df) > 0:
        df = df[df.paragraph.apply(lambda t: len(t) > 0 and t[0].isupper())]
    if len(df) > 0:
        df = df[df.paragraph.apply(len) >= 100]
    if len(df) > 0:
        df = df.drop_duplicates("paragraph")

    return df
