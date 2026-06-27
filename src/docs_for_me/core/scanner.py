from dataclasses import dataclass
from pathlib import Path


DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "vendor",
}


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    relative_path: Path
    size: int


def scan_folder(path: Path, max_files: int = 200) -> list[ScannedFile]:
    root = path.resolve()
    files: list[ScannedFile] = []

    for item in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break

        if _is_ignored(item, root):
            continue

        if item.is_file():
            files.append(
                ScannedFile(
                    path=item,
                    relative_path=item.relative_to(root),
                    size=item.stat().st_size,
                )
            )

    return files


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return True

    return any(part in DEFAULT_IGNORES for part in relative_parts)
