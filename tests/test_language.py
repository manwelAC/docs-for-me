from pathlib import Path

from docs_for_me.core.language import detect_language


def test_detect_language_known_extension() -> None:
    assert detect_language(Path("app.py")) == "Python"
    assert detect_language(Path("app.ts")) == "TypeScript"


def test_detect_language_unknown_extension() -> None:
    assert detect_language(Path("notes.weird")) == "Unknown"
