from pathlib import Path

from docs_for_me.ai.none import NoAIProvider
from docs_for_me.core.folder_docs import document_folder


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
