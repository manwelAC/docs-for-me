from pathlib import Path
import sys

import typer


def write_markdown(markdown: str, out: Path | None, quiet: bool = False) -> None:
    if out is None:
        encoding = sys.stdout.encoding or "utf-8"
        safe_markdown = markdown.encode(encoding, errors="replace").decode(encoding, errors="replace")
        typer.echo(safe_markdown)
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    if not quiet:
        typer.echo(f"Wrote {out}", err=True)
