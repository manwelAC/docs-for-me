from pathlib import Path

from docs_for_me.core.scanner import scan_folder


def test_scan_folder_ignores_common_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("ignored", encoding="utf-8")

    files = scan_folder(tmp_path)

    assert [file.relative_path.as_posix() for file in files] == ["src/app.py"]
