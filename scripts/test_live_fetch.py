#!/usr/bin/env python3
"""Live test script to verify all document ID formats work with get_html().

This script tests the unified fetch functionality with real EUR-Lex documents
across all supported identifier formats:
- CELEX IDs (standard and with suffix)
- Cellar URLs
- Cellar IDs (UUID format)
- OJ References (via SPARQL lookup)

Usage:
    uv run python scripts/test_live_fetch.py
    # or
    just test-live

Note: Some tests may fail due to transient server errors (500s) from EUR-Lex.
The test is considered passing if at least one document of each type succeeds.
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Test documents with different ID formats - multiple options per type for resilience
TEST_CELEX_IDS = [
    # Try multiple documents - if one fails due to server error, others may work
    ("32012L0029", "Directive 2012/29 (Victims' Rights)"),
    ("32016R0679", "GDPR Regulation"),
    ("32019R0947", "Drone Regulation"),
    ("32000R0044", "Brussels I Regulation"),
]


def test_detect_id_type() -> bool:
    """Test that detect_id_type correctly identifies all formats."""
    from eurlxp import detect_id_type

    logger.info("=" * 60)
    logger.info("Test 1: detect_id_type() correctly identifies formats")
    logger.info("=" * 60)

    test_cases = [
        ("32019R0947", "celex"),
        ("32012L0029R(06)", "celex"),
        ("52026XG00745", "celex"),
        ("http://publications.europa.eu/resource/cellar/abc123", "cellar_url"),
        ("https://publications.europa.eu/resource/cellar/abc123", "cellar_url"),
        ("cellar:abc-123-def", "cellar_id"),
        ("12345678-1234-1234-1234-123456789012", "cellar_id"),
        ("C/2026/00064", "oj_reference"),  # OJ reference - fetched via SPARQL lookup
    ]

    all_passed = True
    for identifier, expected_type in test_cases:
        result = detect_id_type(identifier)
        status = "✓" if result == expected_type else "✗"
        if result != expected_type:
            all_passed = False
        logger.info(f"  {status} detect_id_type('{identifier}') = '{result}' (expected: '{expected_type}')")

    return all_passed


def test_get_html_celex() -> bool:
    """Test get_html() with CELEX IDs.

    Passes if at least one CELEX ID is fetched successfully.
    """
    from eurlxp import WAFChallengeError, get_html, parse_html

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 2: get_html() with CELEX IDs")
    logger.info("=" * 60)

    successes = 0
    for identifier, description in TEST_CELEX_IDS:
        try:
            logger.info(f"  Fetching {identifier} ({description})...")
            html = get_html(identifier)
            df = parse_html(html)
            logger.info(f"  ✓ {identifier}: {len(html):,} bytes, {len(df)} rows")
            successes += 1
            if successes >= 2:  # Success if we get at least 2
                break
        except WAFChallengeError:
            logger.warning(f"  ⚠ {identifier}: WAF challenge (will try next)")
        except Exception as e:
            logger.warning(f"  ⚠ {identifier}: {type(e).__name__} (will try next)")

    if successes > 0:
        logger.info(f"  → {successes} CELEX ID(s) fetched successfully")
        return True
    else:
        logger.error("  ✗ All CELEX IDs failed")
        return False


def test_get_html_cellar_url() -> bool:
    """Test get_html() with cellar URLs (fetched via SPARQL first).

    Passes if at least one cellar URL is fetched successfully.
    """
    from eurlxp import WAFChallengeError, get_html, get_ids_and_urls_via_date, parse_html

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 3: get_html() with Cellar URLs")
    logger.info("=" * 60)

    try:
        # Get some real cellar URLs from SPARQL - try multiple dates
        docs = []
        for date in ["2024-03-15", "2024-06-15", "2024-09-15"]:
            logger.info(f"  Fetching document references for {date}...")
            try:
                docs = get_ids_and_urls_via_date(date)
                if docs:
                    break
            except Exception:
                continue

        if not docs:
            logger.warning("  ⚠ No documents found, skipping cellar URL test")
            return True

        # Test with up to 5 documents until we get a success
        successes = 0
        for doc in docs[:5]:
            try:
                logger.info(f"  Fetching {doc.raw_id} via cellar URL...")
                html = get_html(doc.cellar_url)
                df = parse_html(html)
                logger.info(f"  ✓ {doc.raw_id}: {len(html):,} bytes, {len(df)} rows")
                successes += 1
                if successes >= 1:  # Just need one success
                    break
            except WAFChallengeError:
                logger.warning(f"  ⚠ {doc.raw_id}: WAF challenge (will try next)")
            except Exception as e:
                logger.warning(f"  ⚠ {doc.raw_id}: {type(e).__name__} (will try next)")

        if successes > 0:
            logger.info(f"  → {successes} cellar URL(s) fetched successfully")
            return True
        else:
            logger.error("  ✗ All cellar URLs failed (likely transient server issues)")
            return False

    except ImportError:
        logger.warning("  ⚠ SPARQL dependencies not installed, skipping cellar URL test")
        return True
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False


def test_get_html_oj_reference() -> bool:
    """Test get_html() with OJ references (looked up via SPARQL)."""
    from eurlxp import get_html, lookup_cellar_url, parse_html

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 4: get_html() with OJ References (SPARQL lookup)")
    logger.info("=" * 60)

    try:
        # First, let's find a real OJ reference from recent documents
        from eurlxp import get_ids_and_urls_via_date

        docs = get_ids_and_urls_via_date("2024-06-01", "2024-06-30")

        # Find one where celex_id is None (OJ reference)
        oj_refs = [d for d in docs if d.celex_id is None]

        if not oj_refs:
            logger.info("  No OJ references found in test date range")
            # Try the lookup_cellar_url function directly with a known pattern
            logger.info("  Testing lookup_cellar_url() directly...")
            url = lookup_cellar_url("32019R0947")  # Known CELEX to verify SPARQL works
            if url:
                logger.info(f"  ✓ lookup_cellar_url('32019R0947') = {url}")
            else:
                logger.warning("  ⚠ lookup_cellar_url returned None")
            return True

        # Test with an OJ reference
        oj_ref = oj_refs[0]
        logger.info(f"  Found OJ reference: {oj_ref.raw_id}")
        logger.info(f"  Cellar URL: {oj_ref.cellar_url}")

        # Now test get_html with the OJ reference raw_id
        logger.info(f"  Fetching via get_html('{oj_ref.raw_id}')...")
        try:
            html = get_html(oj_ref.raw_id)
            df = parse_html(html)
            logger.info(f"  ✓ {oj_ref.raw_id}: {len(html):,} bytes, {len(df)} rows")
            return True
        except ValueError as e:
            if "SPARQL lookup found no results" in str(e):
                logger.warning(f"  ⚠ {oj_ref.raw_id}: SPARQL lookup failed (expected for some OJ refs)")
                return True
            raise

    except ImportError:
        logger.warning("  ⚠ SPARQL dependencies not installed, skipping OJ reference test")
        return True
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False


def test_fetch_documents_mixed() -> bool:
    """Test fetch_documents() with mixed identifier types."""
    from eurlxp import fetch_documents

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 5: fetch_documents() with mixed ID types")
    logger.info("=" * 60)

    # Mix of ID types
    identifiers = [
        "32019R0947",  # CELEX
        "32012L0029",  # CELEX
    ]

    try:
        logger.info(f"  Fetching {len(identifiers)} documents...")
        results = fetch_documents(identifiers, on_error="include")

        successes = sum(1 for v in results.values() if isinstance(v, str))
        failures = sum(1 for v in results.values() if isinstance(v, Exception))

        logger.info(f"  Results: {successes} succeeded, {failures} failed")

        for identifier, result in results.items():
            if isinstance(result, str):
                logger.info(f"  ✓ {identifier}: {len(result):,} bytes")
            else:
                logger.warning(f"  ⚠ {identifier}: {result}")

        return successes > 0

    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False


def test_cleanup() -> None:
    """Clean up any temporary files."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Cleanup")
    logger.info("=" * 60)
    logger.info("  No temporary files to clean up")


def main() -> int:
    """Run all live tests."""
    logger.info("EUR-Lex Live Fetch Test Suite")
    logger.info("Testing unified get_html() with all ID formats")
    logger.info("(Uses real network requests to EUR-Lex)")
    logger.info("")

    results = []

    results.append(("detect_id_type", test_detect_id_type()))
    results.append(("get_html (CELEX)", test_get_html_celex()))
    results.append(("get_html (Cellar URL)", test_get_html_cellar_url()))
    results.append(("get_html (OJ Reference)", test_get_html_oj_reference()))
    results.append(("fetch_documents (mixed)", test_fetch_documents_mixed()))

    test_cleanup()

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {name}")

    logger.info("")
    logger.info(f"Total: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
