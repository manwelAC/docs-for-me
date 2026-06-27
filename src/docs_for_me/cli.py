from pathlib import Path
from typing import Optional

import typer

from docs_for_me.ai import build_provider
from docs_for_me.core.file_docs import document_file
from docs_for_me.core.folder_docs import document_folder
from docs_for_me.git.change_docs import document_changes
from docs_for_me.render.markdown import write_markdown
from docs_for_me.render.status import StatusReporter

APP_HELP = """
Create Markdown guides for files, folders, and Git changes.

Install once:

  npm install -g docs-for-me

Then run:

  docs-for-me file ".\\app\\Http\\Controllers\\Api\\AnalyticsController.php" --ai none --out analytics-guide.md
  docs-for-me folder ".\\app\\Http\\Controllers\\Api" --ai none --out api-guide.md
  docs-for-me changes --ai none --out changes-guide.md

Optional one-time trial:

  npx docs-for-me --help

AI modes:

  --ai none      Local, fast, no AI provider needed.
  --ai opencode  Uses your installed OpenCode setup for deeper writing.
"""

app = typer.Typer(
    help=APP_HELP,
    no_args_is_help=True,
    rich_markup_mode=None,
)


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
