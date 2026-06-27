from pathlib import Path

from docs_for_me.ai.base import AIProvider, AIResponse, ProgressCallback
from docs_for_me.ai.none import NoAIProvider
from docs_for_me.core.folder_docs import document_folder


class RecordingProvider(AIProvider):
    name = "recording"

    def __init__(self) -> None:
        self.files: list[str] | None = None

    def generate(
        self,
        prompt: str,
        files: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AIResponse:
        self.files = files
        assert files is not None
        assert len(files) == 1
        context = Path(files[0]).read_text(encoding="utf-8")
        assert "## Sampled File Contents" in context
        assert "bookings.ts" in context
        return AIResponse("# AI folder guide\n", used_ai=True)


def test_document_folder_summarizes_content_signals(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "bookings.ts").write_text(
        """
const title = "Bookings"
const status = "Checked In"
function searchBookings() {}
function createBooking() {}
fetch("/api/bookings")
""",
        encoding="utf-8",
    )
    (app / "guests.ts").write_text(
        """
const title = "Guests"
function updateGuestProfile() {}
fetch("/api/guests")
""",
        encoding="utf-8",
    )

    markdown = document_folder(app, NoAIProvider())

    assert "## Overview" in markdown
    assert "## What This Is Based On" in markdown
    assert "bookings" in markdown
    assert "guests" in markdown
    assert "/api/bookings" in markdown
    assert "## Key Files" in markdown


def test_document_folder_uses_single_context_file_for_ai(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    (app / "bookings.ts").write_text('const title = "Bookings"\n', encoding="utf-8")

    provider = RecordingProvider()
    markdown = document_folder(app, provider)

    assert markdown == "# AI folder guide\n"
    assert provider.files is not None
