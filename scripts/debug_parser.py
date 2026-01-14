#!/usr/bin/env python3
"""Debug script to investigate parser issues with different EUR-Lex document formats."""

import eurlxp as el
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ETree


def analyze_document(celex_id: str) -> None:
    """Analyze a document's structure and parsing results."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {celex_id}")
    print(f"{'='*60}")

    html = el.get_html_by_celex_id(celex_id)
    print(f"HTML length: {len(html)} bytes")

    # Find all unique CSS classes
    soup = BeautifulSoup(html, "lxml-xml")
    all_classes: set[str] = set()
    for tag in soup.find_all(True):
        css_class = tag.get("class")
        if css_class:
            if isinstance(css_class, list):
                all_classes.update(css_class)
            else:
                all_classes.add(css_class)

    print(f"\nUnique CSS classes ({len(all_classes)}):")
    for c in sorted(all_classes):
        count = len(soup.find_all(True, class_=c))
        if count > 0:
            print(f"  {c}: {count}")

    # Count potential text-bearing elements
    text_classes = ["normal", "oj-normal", "Normal", "doc-ti", "oj-doc-ti", "Titreobjet"]
    print(f"\nText-bearing elements (BeautifulSoup):")
    for cls in text_classes:
        elements = soup.find_all("p", class_=cls)
        if elements:
            print(f"  p.{cls}: {len(elements)}")

    # Parse with current parser
    df = el.parse_html(html)
    print(f"\nParser result: {df.shape[0]} rows")
    if len(df) > 0:
        print(f"  First: {df.iloc[0]['text'][:60]}...")
        if len(df) > 1:
            print(f"  Last: {df.iloc[-1]['text'][:60]}...")


if __name__ == "__main__":
    # Test different document types
    test_docs = [
        "32019R0947",   # Regulation (OJ format)
        "52026PC0002",  # Commission proposal (different format)
        "32025L0002",   # Directive (OJ format)
    ]

    for doc in test_docs:
        try:
            analyze_document(doc)
        except Exception as e:
            print(f"Error with {doc}: {e}")
