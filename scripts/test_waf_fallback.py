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


def test_sparql_direct() -> None:
    """Test SPARQL endpoint directly."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 3: Direct SPARQL query (no HTML scraping)")
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
    test_sparql_direct()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Tests complete!")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
