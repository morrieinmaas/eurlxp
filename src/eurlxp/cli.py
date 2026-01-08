"""Command-line interface for eurlxp."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="eurlxp",
    help="EUR-Lex document parser - fetch and parse EU legal documents.",
    add_completion=False,
)
console = Console()


@app.command()
def fetch(
    celex_id: Annotated[str, typer.Argument(help="CELEX ID of the document (e.g., 32019R0947)")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    language: Annotated[str, typer.Option("--language", "-l", help="Language code")] = "en",
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: html, csv, json")] = "html",
) -> None:
    """Fetch an EUR-Lex document by CELEX ID."""
    from eurlxp.client import get_html_by_celex_id
    from eurlxp.parser import parse_html

    with console.status(f"Fetching document {celex_id}..."):
        try:
            html = get_html_by_celex_id(celex_id, language)
        except Exception as e:
            console.print(f"[red]Error fetching document: {e}[/red]")
            raise typer.Exit(1) from None

    content: str
    if format == "html":
        content = html
    elif format in ("csv", "json"):
        df = parse_html(html)
        if df.empty:
            console.print("[yellow]Warning: No content parsed from document[/yellow]")
            content = "" if format == "csv" else "[]"
        else:
            csv_content = df.to_csv(index=False)
            json_content = df.to_json(orient="records", indent=2)
            content = csv_content if format == "csv" else (json_content or "[]")
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(content)
        console.print(f"[green]Saved to {output}[/green]")
    else:
        console.print(content)


@app.command()
def parse(
    input_file: Annotated[Path, typer.Argument(help="Input HTML file to parse")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: csv, json")] = "csv",
) -> None:
    """Parse a local EUR-Lex HTML file."""
    from eurlxp.parser import parse_html

    if not input_file.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(1)

    html = input_file.read_text()
    df = parse_html(html)

    if df.empty:
        console.print("[yellow]Warning: No content parsed from document[/yellow]")
        raise typer.Exit(0)

    content: str
    if format == "csv":
        content = df.to_csv(index=False) or ""
    elif format == "json":
        content = df.to_json(orient="records", indent=2) or "[]"
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(content)
        console.print(f"[green]Saved to {output}[/green]")
    else:
        console.print(content)


@app.command()
def info(
    celex_id: Annotated[str, typer.Argument(help="CELEX ID of the document")],
    language: Annotated[str, typer.Option("--language", "-l", help="Language code")] = "en",
) -> None:
    """Show information about an EUR-Lex document."""
    from eurlxp.client import get_html_by_celex_id
    from eurlxp.parser import parse_html

    with console.status(f"Fetching document {celex_id}..."):
        try:
            html = get_html_by_celex_id(celex_id, language)
        except Exception as e:
            console.print(f"[red]Error fetching document: {e}[/red]")
            raise typer.Exit(1) from None

    df = parse_html(html)

    table = Table(title=f"Document: {celex_id}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("CELEX ID", celex_id)
    table.add_row("Language", language)
    table.add_row("Total rows", str(len(df)))

    if "article" in df.columns:
        article_col = df["article"]
        unique_articles: int = article_col[article_col.notna()].nunique()  # type: ignore[assignment]
        table.add_row("Unique articles", str(unique_articles))

    if "document" in df.columns:
        doc_col = df["document"].dropna()
        if len(doc_col) > 0:
            doc_title = str(doc_col.iloc[0])[:80]
            table.add_row("Document title", doc_title)

    console.print(table)


@app.command()
def celex(
    slash_notation: Annotated[str, typer.Argument(help="Slash notation (e.g., 2019/947)")],
    document_type: Annotated[str, typer.Option("--type", "-t", help="Document type (R, L, D, etc.)")] = "R",
    sector: Annotated[str, typer.Option("--sector", "-s", help="Sector ID")] = "3",
) -> None:
    """Convert slash notation to CELEX ID."""
    from eurlxp.parser import get_celex_id

    try:
        celex_id = get_celex_id(slash_notation, document_type, sector)
        console.print(f"[green]{celex_id}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def version() -> None:
    """Show version information."""
    from eurlxp import __version__

    console.print(f"eurlxp version [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
