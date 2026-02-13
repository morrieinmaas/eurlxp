"""Snapshot tests for EUR-Lex document parsing.

These tests parse real EUR-Lex HTML fixtures and snapshot the full DataFrame output.
Any change to parser behavior that affects the output will show up as a snapshot diff,
making it easy to spot intentional improvements vs accidental regressions.

To update snapshots after an intentional parser change:
    pytest tests/test_snapshot.py --snapshot-update
"""

from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

from eurlxp.parser import parse_html

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class CSVSnapshotExtension(SingleFileSnapshotExtension):
    """Snapshot extension that stores DataFrames as .csv files for readable diffs."""

    _write_mode = WriteMode.TEXT
    _file_extension = "csv"

    def serialize(self, data: str, **kwargs) -> str:  # noqa: ARG002
        return data


@pytest.fixture
def snapshot_csv(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(CSVSnapshotExtension)


def _load_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {name} not found — run fetch script to download")
    return path.read_text()


def _df_to_snapshot_csv(df) -> str:
    """Convert DataFrame to a stable CSV string for snapshot comparison."""
    return df.to_csv(index=False)


class TestCRASnapshot:
    """Snapshot tests for the Cyber Resilience Act (32024R2847)."""

    @pytest.fixture
    def cra_html(self) -> str:
        return _load_fixture("cra_32024R2847.html")

    def test_full_parse(self, cra_html: str, snapshot_csv: SnapshotAssertion) -> None:
        """Full parse output — catches any change in row count, text, or metadata."""
        df = parse_html(cra_html)
        assert _df_to_snapshot_csv(df) == snapshot_csv

    def test_row_count(self, cra_html: str) -> None:
        """Sanity check: CRA should produce a substantial number of rows."""
        df = parse_html(cra_html)
        assert len(df) > 1000, f"Expected >1000 rows, got {len(df)}"

    def test_articles_present(self, cra_html: str) -> None:
        """CRA has 71 articles — verify they're all parsed."""
        df = parse_html(cra_html)
        articles = df["article"].dropna().unique()
        assert len(articles) == 71, f"Expected 71 articles, got {len(articles)}: {sorted(articles)}"

    def test_article_1_content(self, cra_html: str, snapshot: SnapshotAssertion) -> None:
        """Snapshot Article 1 specifically — a key article that should be stable."""
        df = parse_html(cra_html)
        article_1 = df[df["article"] == "1"]
        records = article_1[["text", "paragraph", "group", "section"]].to_dict(orient="records")
        assert records == snapshot

    def test_preamble(self, cra_html: str, snapshot: SnapshotAssertion) -> None:
        """Snapshot preamble rows (before any article)."""
        df = parse_html(cra_html)
        preamble = df[df["article"].isna()]
        records = preamble[["text"]].to_dict(orient="records")
        assert records == snapshot

    def test_sections_and_groups(self, cra_html: str, snapshot: SnapshotAssertion) -> None:
        """Snapshot the unique section/group structure."""
        df = parse_html(cra_html)
        structure = (
            df[df["article"].notna()]
            .groupby("article", sort=False)
            .first()[["section", "group"]]
            .reset_index()
            .to_dict(orient="records")
        )
        assert structure == snapshot


class TestAIActSnapshot:
    """Snapshot tests for the AI Act (32024R1689)."""

    @pytest.fixture
    def ai_act_html(self) -> str:
        return _load_fixture("ai_act_32024R1689.html")

    def test_full_parse(self, ai_act_html: str, snapshot_csv: SnapshotAssertion) -> None:
        """Full parse output for the AI Act."""
        df = parse_html(ai_act_html)
        assert _df_to_snapshot_csv(df) == snapshot_csv

    def test_row_count(self, ai_act_html: str) -> None:
        """AI Act should produce a substantial number of rows."""
        df = parse_html(ai_act_html)
        assert len(df) > 1500, f"Expected >1500 rows, got {len(df)}"

    def test_article_1_content(self, ai_act_html: str, snapshot: SnapshotAssertion) -> None:
        """Snapshot Article 1 of the AI Act."""
        df = parse_html(ai_act_html)
        article_1 = df[df["article"] == "1"]
        records = article_1[["text", "paragraph", "group", "section"]].to_dict(orient="records")
        assert records == snapshot

    def test_sections_and_groups(self, ai_act_html: str, snapshot: SnapshotAssertion) -> None:
        """Snapshot the unique section/group structure of the AI Act."""
        df = parse_html(ai_act_html)
        structure = (
            df[df["article"].notna()]
            .groupby("article", sort=False)
            .first()[["section", "group"]]
            .reset_index()
            .to_dict(orient="records")
        )
        assert structure == snapshot
