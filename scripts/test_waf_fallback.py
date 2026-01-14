#!/usr/bin/env python3
"""Test script to verify WAF detection and SPARQL fallback behavior.

This script tests the library's ability to:
1. Detect AWS WAF challenges from EUR-Lex
2. Automatically fall back to SPARQL when blocked
3. Compare behavior with and without fallback

Usage:
    uv run python scripts/test_waf_fallback.py
    # or
    make test-waf
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_with_sparql_fallback() -> None:
    """Test fetching with SPARQL fallback enabled (default)."""
    from eurlxp import ClientConfig, EURLexClient

    logger.info("=" * 60)
    logger.info("Test 1: Fetching with SPARQL fallback ENABLED (default)")
    logger.info("=" * 60)

    config = ClientConfig(sparql_fallback=True)
    with EURLexClient(config=config) as client:
        try:
            html = client.get_html_by_celex_id("32019R0947")
            if "SPARQL fallback" in html:
                logger.info("✓ WAF detected, SPARQL fallback was used")
                logger.info("  Returned minimal HTML from SPARQL metadata")
            else:
                logger.info("✓ Direct HTML fetch succeeded (no WAF block)")
            logger.info(f"  HTML length: {len(html)} characters")
            logger.info(f"  First 200 chars: {html[:200]}...")
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")


def test_without_sparql_fallback() -> None:
    """Test fetching with SPARQL fallback disabled."""
    from eurlxp import ClientConfig, EURLexClient, WAFChallengeError

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 2: Fetching with SPARQL fallback DISABLED")
    logger.info("=" * 60)

    config = ClientConfig(sparql_fallback=False)
    with EURLexClient(config=config) as client:
        try:
            html = client.get_html_by_celex_id("32019R0947")
            logger.info("✓ Direct HTML fetch succeeded (no WAF block)")
            logger.info(f"  HTML length: {len(html)} characters")
        except WAFChallengeError as e:
            logger.info("✓ WAFChallengeError raised as expected when fallback disabled")
            logger.info(f"  Error: {e}")
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}")


def test_sparql_fallback_fetches_real_content() -> None:
    """Test that SPARQL fallback fetches actual document content via RDF graph traversal."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 3: SPARQL fallback fetches REAL document content")
    logger.info("=" * 60)

    try:
        from eurlxp.client import _fetch_html_via_sparql
        from eurlxp.parser import parse_html

        # Test with a known document
        celex_id = "32025L0002"
        logger.info(f"Testing _fetch_html_via_sparql('{celex_id}')...")

        html = _fetch_html_via_sparql(celex_id, "en")

        # Verify it's real content, not placeholder
        if "SPARQL fallback" in html and "Full HTML content unavailable" in html:
            logger.error("✗ SPARQL fallback returned placeholder HTML instead of real content!")
            return

        logger.info(f"✓ Fetched {len(html)} bytes of HTML")
        logger.info(f"  First 150 chars: {html[:150]}...")

        # Parse and verify we get actual content
        df = parse_html(html)
        logger.info(f"✓ Parsed to DataFrame with {len(df)} rows")

        if len(df) > 0:
            first_text = df.iloc[0]["text"][:80] if len(df.iloc[0]["text"]) > 80 else df.iloc[0]["text"]
            logger.info(f"  First row text: {first_text}...")
            logger.info("✓ SPARQL fallback successfully fetches real document content!")
        else:
            logger.warning("⚠ DataFrame is empty - parsing may have issues")

    except ImportError as e:
        logger.warning(f"✗ SPARQL dependencies not installed: {e}")
        logger.warning("  Run: pip install eurlxp[sparql]")
    except Exception as e:
        logger.error(f"✗ Error: {e}")


def test_parser_different_formats() -> None:
    """Test parser with different EUR-Lex document formats."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 4: Parser handles different document formats")
    logger.info("=" * 60)

    try:
        import eurlxp as el

        test_cases = [
            ("2026/2", "Commission proposal format"),
            ("1983/2", "Older document format"),
        ]

        for slash_notation, description in test_cases:
            logger.info(f"\nTesting {slash_notation} ({description})...")
            possible_docs = el.guess_celex_ids_via_eurlex(slash_notation)
            logger.info(f"  Found CELEX IDs: {possible_docs[:3]}")

            for doc in possible_docs[:2]:  # Test first 2
                try:
                    html = el.get_html_by_celex_id(doc)
                    df = el.parse_html(html)
                    logger.info(f"  {doc}: {df.shape} columns={df.columns.tolist()}")
                    if len(df) > 0:
                        first_text = df.iloc[0]["text"][:60]
                        logger.info(f"    First: {first_text}...")
                    else:
                        logger.warning(f"    ⚠ Empty DataFrame")
                except Exception as e:
                    logger.error(f"  {doc}: Error - {e}")

        logger.info("✓ Parser format tests complete")

    except ImportError as e:
        logger.warning(f"✗ Dependencies not installed: {e}")
    except Exception as e:
        logger.error(f"✗ Error: {e}")


def test_pdf_extraction() -> None:
    """Test PDF extraction for documents without XHTML."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 5: PDF extraction for old documents")
    logger.info("=" * 60)

    try:
        from eurlxp.client import _fetch_html_via_sparql
        from eurlxp.parser import parse_html

        # Test with a 1983 document that only has PDF
        celex_id = "31983R0002"
        logger.info(f"Testing PDF extraction for {celex_id}...")

        html = _fetch_html_via_sparql(celex_id, "en", include_pdf=True)
        logger.info(f"✓ Fetched {len(html)} bytes via PDF extraction")

        df = parse_html(html)
        logger.info(f"✓ Parsed to DataFrame with {len(df)} rows")

        if len(df) > 0:
            first_text = df.iloc[0]["text"][:80]
            logger.info(f"  First row: {first_text}...")
            logger.info("✓ PDF extraction successfully extracts document content!")
        else:
            logger.warning("⚠ DataFrame is empty")

    except ImportError as e:
        logger.warning(f"✗ Dependencies not installed: {e}")
    except Exception as e:
        logger.error(f"✗ Error: {e}")


def test_sparql_direct() -> None:
    """Test SPARQL endpoint directly."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 6: Direct SPARQL query (no HTML scraping)")
    logger.info("=" * 60)

    try:
        from eurlxp import get_documents, guess_celex_ids_via_eurlex

        # Test guess_celex_ids_via_eurlex
        logger.info("Testing guess_celex_ids_via_eurlex('2019/947')...")
        celex_ids = guess_celex_ids_via_eurlex("2019/947")
        logger.info(f"✓ Found CELEX IDs: {celex_ids}")

        # Test get_documents
        logger.info("Testing get_documents(types=['REG'], limit=3)...")
        docs = get_documents(types=["REG"], limit=3)
        logger.info(f"✓ Found {len(docs)} documents:")
        for doc in docs:
            logger.info(f"  - {doc['celex']}: {doc['type']} ({doc['date']})")

    except ImportError:
        logger.warning("✗ SPARQL dependencies not installed. Run: pip install eurlxp[sparql]")
    except Exception as e:
        logger.error(f"✗ SPARQL error: {e}")


def main() -> int:
    """Run all tests."""
    logger.info("EUR-Lex WAF Fallback Test Suite")
    logger.info("Testing library behavior with EUR-Lex bot detection")
    logger.info("")

    test_with_sparql_fallback()
    test_without_sparql_fallback()
    test_sparql_fallback_fetches_real_content()
    test_parser_different_formats()
    test_pdf_extraction()
    test_sparql_direct()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Tests complete!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
