import subprocess


def read_diff(staged: bool = False, since: str | None = None) -> str:
    command = ["git", "diff"]

    if since:
        command.append(since)
    elif staged:
        command.append("--staged")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout
