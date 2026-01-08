"""Pytest configuration and fixtures."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (require network)")


@pytest.fixture
def sample_html() -> str:
    """Sample EUR-Lex HTML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Test Document</title></head>
<body>
    <p class="doc-ti">COMMISSION REGULATION (EU) 2019/947</p>
    <p class="ti-art">Article 1</p>
    <p class="sti-art">Subject matter</p>
    <p class="normal">1. This Regulation lays down detailed provisions.</p>
    <p class="normal">2. This Regulation applies to all operators.</p>
    <p class="ti-art">Article 2</p>
    <p class="sti-art">Definitions</p>
    <p class="normal">For the purposes of this Regulation, the following definitions apply.</p>
</body>
</html>"""


@pytest.fixture
def sample_html_with_groups() -> str:
    """Sample EUR-Lex HTML with group titles."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Test Document</title></head>
<body>
    <p class="doc-ti">ANNEX</p>
    <p class="ti-grseq-1">Part A - Requirements</p>
    <p class="normal">Requirement text here.</p>
    <p class="ti-grseq-1">Part B - Procedures</p>
    <p class="normal">Procedure text here.</p>
</body>
</html>"""
