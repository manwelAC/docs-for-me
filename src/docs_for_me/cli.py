from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from docs_for_me.ai import build_provider
from docs_for_me.core.file_docs import document_file
from docs_for_me.core.folder_docs import document_folder
from docs_for_me.git.change_docs import document_changes
from docs_for_me.render.markdown import write_markdown
from docs_for_me.render.status import StatusReporter

APP_HELP = """
\b
docs-for-me
===========

Make readable Markdown guides for files, folders, and Git changes.

\b
Install once:

  npm install -g docs-for-me

Start here:

  docs-for-me file PATH --ai none --out file-guide.md

  docs-for-me folder PATH --ai none --out folder-guide.md

  docs-for-me changes --ai none --out changes-guide.md

\b
AI choices:

  --ai none      Local and fast. No AI provider needed.

  --ai opencode  Uses your installed OpenCode setup for deeper writing.

\b
One-time trial:

  npx docs-for-me --help

Tip: wrap paths in quotes when they contain spaces or special characters.
"""

console = Console()

app = typer.Typer(
    help=APP_HELP,
    context_settings={"help_option_names": ["--_internal-help"]},
    rich_markup_mode=None,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    help_requested: bool = typer.Option(False, "--help", "-h", help="Show help and exit.", is_eager=True),
) -> None:
    """Create docs for files, folders, and Git changes."""
    if help_requested or ctx.invoked_subcommand is None:
        _render_help()
        raise typer.Exit()


def _render_help() -> None:
    title = Text()
    title.append("docs-for-me", style="bold bright_cyan")
    title.append("\n")
    title.append("Turn Git changes into review guides and commit-ready messages.", style="white")

    console.print()
    console.print(
        Panel(
            title,
            border_style="bright_cyan",
            box=box.DOUBLE,
            padding=(1, 4),
        )
    )

    console.print("[bold bright_green]Main workflow[/bold bright_green]")
    console.print("  [bright_white]docs-for-me changes --ai none --out changes-guide.md[/bright_white]")
    console.print("  [dim]Review your diff, understand changed flows, and copy the generated commit message.[/dim]\n")

    commands = Table(
        title="Commands",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold bright_cyan",
        show_lines=True,
    )
    commands.add_column("Use Case", style="bold white", no_wrap=True)
    commands.add_column("Command", style="bright_white")
    commands.add_row("Pre-commit guide", "docs-for-me changes --ai none --out changes-guide.md")
    commands.add_row("Staged changes", "docs-for-me changes --staged --ai none --out changes-guide.md")
    commands.add_row("AI changes guide", "docs-for-me changes --ai opencode --out changes-ai-guide.md")
    commands.add_row("One file", 'docs-for-me file "PATH" --ai none --out file-guide.md')
    commands.add_row("Folder", 'docs-for-me folder "PATH" --ai none --out folder-guide.md')
    console.print(commands)

    commit = Table(
        title="Commit Message Output",
        box=box.SIMPLE,
        border_style="yellow",
        header_style="bold bright_yellow",
        show_lines=False,
    )
    commit.add_column("Part", style="bold white", no_wrap=True)
    commit.add_column("What It Gives You", style="bright_white")
    commit.add_row("Subject", "A precise first line for the commit.")
    commit.add_row("Body", "Added, Updated, Refactored, and Removed sections when visible.")
    commit.add_row("Context", "Affected files, visible changed areas, and diff size.")
    console.print(commit)

    modes = Table(
        title="AI Choices",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold bright_green",
        show_lines=False,
    )
    modes.add_column("Mode", style="bold white", no_wrap=True)
    modes.add_column("Use When", style="bright_white")
    modes.add_row("--ai none", "You want local, fast docs with no AI provider.")
    modes.add_row("--ai opencode", "You want OpenCode to write a deeper guide.")
    console.print(modes)

    console.print("[bold bright_yellow]Install[/bold bright_yellow]")
    console.print("  [bright_white]npm install -g docs-for-me[/bright_white]")
    console.print("[bold bright_yellow]One-time trial[/bold bright_yellow]")
    console.print("  [bright_white]npx docs-for-me --help[/bright_white]\n")
    console.print("[dim]Tip: wrap paths in quotes when they contain spaces or special characters.[/dim]")
    console.print("[dim]Commands: file, folder, changes[/dim]")
    console.print()


@app.command()
def file(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write Markdown to this file."),
    ai: str = typer.Option("opencode", "--ai", help="AI provider: opencode or none."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name for the AI provider."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Hide progress messages."),
) -> None:
    """
    Create a guide for one file.

    Example:

      docs-for-me file ".\\app\\Http\\Controllers\\Api\\AnalyticsController.php" --ai none --out analytics-guide.md
    """
    status = StatusReporter(quiet=quiet)
    status.step(f"Reading file: {path}")
    provider = build_provider(ai, model=model)
    status.step(f"Preparing documentation with provider: {provider.name}")
    if provider.name != "none":
        status.step("Waiting for AI response. This can take a moment...")
    markdown = document_file(path, provider, on_progress=status.step)
    status.step("Writing Markdown output")
    write_markdown(markdown, out, quiet=quiet)
    status.done("Documentation ready.")


@app.command()
def folder(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write Markdown to this file."),
    ai: str = typer.Option("opencode", "--ai", help="AI provider: opencode or none."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name for the AI provider."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Hide progress messages."),
) -> None:
    """
    Create a guide for one folder.

    Example:

      docs-for-me folder ".\\app\\Http\\Controllers\\Api" --ai none --out api-guide.md
    """
    status = StatusReporter(quiet=quiet)
    status.step(f"Scanning folder: {path}")
    provider = build_provider(ai, model=model)
    status.step(f"Preparing folder guide with provider: {provider.name}")
    if provider.name != "none":
        status.step("Waiting for AI response. Large folders may take longer...")
    markdown = document_folder(path, provider, on_progress=status.step)
    status.step("Writing Markdown output")
    write_markdown(markdown, out, quiet=quiet)
    status.done("Folder guide ready.")


@app.command()
def changes(
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write Markdown to this file."),
    staged: bool = typer.Option(False, "--staged", help="Explain staged changes."),
    since: Optional[str] = typer.Option(None, "--since", help="Explain changes since a Git ref."),
    ai: str = typer.Option("opencode", "--ai", help="AI provider: opencode or none."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name for the AI provider."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Hide progress messages."),
) -> None:
    """
    Create a pre-commit guide for your Git changes.

    Example:

      docs-for-me changes --ai none --out changes-guide.md
    """
    status = StatusReporter(quiet=quiet)
    mode = f"since {since}" if since else "staged changes" if staged else "unstaged changes"
    status.step(f"Reading Git diff for {mode}")
    provider = build_provider(ai, model=model)
    status.step(f"Preparing change guide with provider: {provider.name}")
    if provider.name != "none":
        status.step("Waiting for AI response...")
    markdown = document_changes(provider, staged=staged, since=since, on_progress=status.step)
    status.step("Writing Markdown output")
    write_markdown(markdown, out, quiet=quiet)
    status.done("Change guide ready.")


if __name__ == "__main__":
    app()
