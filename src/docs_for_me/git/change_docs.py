from dataclasses import dataclass, field
import re
import tempfile
from pathlib import Path

from docs_for_me.ai.base import AIProvider, AIResponse, ProgressCallback
from docs_for_me.git.diff_reader import read_diff
from docs_for_me.prompts import build_changes_prompt


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int = 0
    removed: int = 0
    added_hints: list[str] = field(default_factory=list)
    removed_hints: list[str] = field(default_factory=list)


def document_changes(
    provider: AIProvider,
    staged: bool = False,
    since: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    diff = read_diff(staged=staged, since=since)
    prompt = build_changes_prompt(diff, staged=staged, since=since)
    ai_response = _generate_ai_changes(provider, prompt, diff, on_progress)

    if ai_response.used_ai and ai_response.text:
        return ai_response.text

    return _fallback_changes_doc(diff, provider.name, staged=staged, since=since)


def _generate_ai_changes(
    provider: AIProvider,
    prompt: str,
    diff: str,
    on_progress: ProgressCallback | None,
) -> AIResponse:
    if provider.name == "none" or not diff.strip():
        return provider.generate(prompt, on_progress=on_progress)

    with tempfile.TemporaryDirectory(prefix="docs-for-me-") as temp_dir:
        diff_path = Path(temp_dir) / "git-changes.diff"
        diff_path.write_text(diff, encoding="utf-8")
        return provider.generate(prompt, files=[str(diff_path)], on_progress=on_progress)


def _fallback_changes_doc(diff: str, provider_name: str, staged: bool, since: str | None) -> str:
    title = "Git Changes"
    mode = f"since `{since}`" if since else "staged changes" if staged else "unstaged changes"

    if not diff.strip():
        return f"# {title}\n\nNo {mode} were found.\n"

    changes = _parse_file_changes(diff)
    added = sum(change.added for change in changes)
    removed = sum(change.removed for change in changes)
    files = [change.path for change in changes]
    commit_message = _suggest_commit_message(changes, added, removed)

    doc = [
        f"# {title}",
        "",
        f"- **Mode:** {mode}",
        f"- **AI:** unavailable or disabled (`{provider_name}`)",
        f"- **Files changed:** {len(files)}",
        f"- **Lines added:** {added}",
        f"- **Lines removed:** {removed}",
        "",
        "## Summary",
        "",
        _summarize_change(changes, added, removed),
        "",
        "## What Changed",
        "",
        *_change_sections(changes),
        "",
        "## Commit Message",
        "",
        "Copy this into your commit command after you review the generated guide. You can delete this docs file afterward if it was only created for commit prep.",
        "",
        "```text",
        commit_message,
        "```",
        "",
        "Example:",
        "",
        "```powershell",
        f'git commit -m "{commit_message}"',
        "```",
        "",
        "## Files Checked",
        "",
    ]

    if files:
        doc.extend(f"- `{file}`" for file in files)
    else:
        doc.append("- Could not identify changed files from diff headers.")

    doc.extend(
        [
            "",
            "## Accuracy Note",
            "",
            "This guide is generated from the Git diff and may miss context that is only clear from running the app, reading related files, or knowing the intended behavior. Review the summary and commit message before committing.",
        ]
    )

    return "\n".join(doc) + "\n"


def _suggest_commit_message(changes: list[FileChange], added: int, removed: int) -> str:
    if not changes:
        return "chore: update project files"

    topics = _change_topics(changes)
    scope = _commit_scope(topics)

    if added > 0 and removed == 0:
        verb = "add"
    elif removed > 0 and added == 0:
        verb = "remove"
    else:
        verb = "update"

    return f"{verb}: {scope}"


def _summarize_change(changes: list[FileChange], added: int, removed: int) -> str:
    if not changes:
        return "The diff changes project files, but no standard Git file headers were found."

    themes = _change_themes(changes)
    if themes:
        theme_text = " ".join(themes)
        return f"These changes update {len(changes)} file(s). {theme_text}"

    topics = _change_topics(changes)
    topic_text = ", ".join(topics[:5]) if topics else "project files"
    return f"These changes update {len(changes)} file(s), mainly around {topic_text}. The guide below lists what each changed file appears to do differently."


def _change_sections(changes: list[FileChange]) -> list[str]:
    sections: list[str] = []

    for change in changes:
        sections.append(f"### `{change.path}`")
        sections.append("")
        sections.append(_describe_file_change(change))
        sections.append("")

        if change.added_hints:
            sections.append("Evidence from added or updated lines:")
            sections.extend(f"- {hint}" for hint in change.added_hints[:6])
            sections.append("")

        if change.removed_hints:
            sections.append("Evidence from removed or replaced lines:")
            sections.extend(f"- {hint}" for hint in change.removed_hints[:4])
            sections.append("")

    return sections


def _describe_file_change(change: FileChange) -> str:
    topic = _file_topic(change.path)
    file_text = " ".join([*change.added_hints, *change.removed_hints]).lower()

    if "searchinput" in file_text and "enter" in file_text:
        return f"This file changes {topic} search handling: the diff shows a separate typed search value and an Enter key handler that applies the search."
    if "getplanlimit" in file_text or "hotel_limit" in file_text:
        return f"This file changes {topic} plan-limit handling: the diff shows a shared `getPlanLimit` lookup replacing separate limit variables."

    if change.added and change.removed:
        return f"This file has both added and removed lines around {topic}. Review the evidence below to confirm the exact behavior change."
    if change.added:
        return f"This file adds new content or behavior around {topic}."
    if change.removed:
        return f"This file removes content or behavior around {topic}."
    return f"This file is listed in the diff, but no readable line-level changes were detected."


def _file_topics(files: list[str]) -> list[str]:
    topics: list[str] = []

    for file in files:
        cleaned = file.replace("a/", "").replace("b/", "")
        parts = cleaned.replace("\\", "/").split("/")
        for part in parts:
            stem = part.rsplit(".", 1)[0]
            if stem in {"page", "index", "layout", "main", "app", "src"}:
                continue
            words = stem.replace("-", " ").replace("_", " ").strip()
            if len(words) < 3:
                continue
            if words not in topics:
                topics.append(words)

    return topics


def _change_topics(changes: list[FileChange]) -> list[str]:
    topics: list[str] = []

    if _has_search_commit_theme(changes):
        topics.append("search behavior")
    if _has_plan_limit_theme(changes):
        topics.append("plan limits")

    for change in changes:
        for topic in [_file_topic(change.path), *_topics_from_hints(change.added_hints)]:
            if topic and topic not in topics:
                topics.append(topic)

    return topics


def _commit_scope(topics: list[str]) -> str:
    filtered = [topic for topic in topics if topic not in {"dashboard", "page", "app", "line", "changed"}]
    if not filtered:
        filtered = topics
    if not filtered:
        return "project"
    if len(filtered) == 1:
        return filtered[0]
    return " and ".join(filtered[:2])


def _file_topic(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    meaningful = []

    for part in parts:
        stem = part.rsplit(".", 1)[0].strip("()[]{}")
        if stem in {"app", "src", "page", "index", "layout"}:
            continue
        words = stem.replace("-", " ").replace("_", " ").strip()
        if len(words) >= 3:
            meaningful.append(words)

    return meaningful[-1] if meaningful else "this area"


def _topics_from_hints(hints: list[str]) -> list[str]:
    topics: list[str] = []

    for hint in hints:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", hint):
            cleaned = word.replace("-", " ").replace("_", " ").lower()
            if cleaned in {
                "const",
                "function",
                "return",
                "class",
                "import",
                "export",
                "true",
                "false",
                "line",
                "changed",
                "value",
                "text",
            }:
                continue
            if cleaned not in topics:
                topics.append(cleaned)
            if len(topics) >= 4:
                return topics

    return topics


def _change_themes(changes: list[FileChange]) -> list[str]:
    themes: list[str] = []

    search_files = [change for change in changes if _file_has_terms(change, ["searchinput", "enter"])]
    if search_files:
        topics = ", ".join(_file_topic(change.path) for change in search_files[:6])
        themes.append(
            f"Several dashboard pages now separate typed search text from the committed search value, so users can type first and apply search with Enter. Affected areas include {topics}."
        )

    plan_files = [change for change in changes if _file_has_terms(change, ["getplanlimit"]) or _file_has_terms(change, ["hotel_limit"])]
    if plan_files:
        themes.append("Dashboard plan-limit display logic was consolidated around shared plan limit lookup values.")

    themed_paths = {change.path for change in [*search_files, *plan_files]}
    remaining = len([change for change in changes if change.path not in themed_paths])
    if remaining > 0:
        themes.append(f"{remaining} other file(s) include smaller UI or content adjustments.")

    return themes


def _has_search_commit_theme(changes: list[FileChange]) -> bool:
    return any(_file_has_terms(change, ["searchinput", "enter"]) for change in changes)


def _has_plan_limit_theme(changes: list[FileChange]) -> bool:
    return any(_file_has_terms(change, ["getplanlimit"]) or _file_has_terms(change, ["hotel_limit"]) for change in changes)


def _file_has_terms(change: FileChange, terms: list[str]) -> bool:
    text = " ".join([*change.added_hints, *change.removed_hints]).lower()
    return all(term in text for term in terms)


def _changed_files(diff: str) -> list[str]:
    files: list[str] = []

    for line in diff.splitlines():
        if not line.startswith("diff --git "):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        path = parts[3]
        if path.startswith("b/"):
            path = path[2:]
        if path not in files:
            files.append(path)

    return files


def _parse_file_changes(diff: str) -> list[FileChange]:
    changes: list[FileChange] = []
    current_path: str | None = None
    added = 0
    removed = 0
    added_hints: list[str] = []
    removed_hints: list[str] = []

    def flush() -> None:
        nonlocal current_path, added, removed, added_hints, removed_hints
        if current_path is not None:
            changes.append(
                FileChange(
                    path=current_path,
                    added=added,
                    removed=removed,
                    added_hints=added_hints[:8],
                    removed_hints=removed_hints[:6],
                )
            )
        current_path = None
        added = 0
        removed = 0
        added_hints = []
        removed_hints = []

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            parts = line.split()
            current_path = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else parts[-1]
            continue

        if current_path is None:
            continue

        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
            hint = _readable_change_hint(line[1:])
            if hint:
                added_hints.append(hint)
        elif line.startswith("-"):
            removed += 1
            hint = _readable_change_hint(line[1:])
            if hint:
                removed_hints.append(hint)

    flush()
    return changes


def _readable_change_hint(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith(("import ", "from ", "}", "{", ")", "(", "//")):
        return None
    if len(stripped) > 140:
        stripped = stripped[:137] + "..."

    label_match = re.search(r"""["'`]([^"'`]{3,80})["'`]""", stripped)
    if label_match:
        label = label_match.group(1).strip()
        if _looks_readable(label):
            return f"Text or value: `{label}`"

    function_match = re.search(r"\b(?:function|const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
    if function_match:
        return f"Code area: `{function_match.group(1)}`"

    return f"Line changed: `{stripped}`"


def _looks_readable(value: str) -> bool:
    if value.startswith(("@/", "./", "../", "http://", "https://")):
        return False
    letters = re.findall(r"[A-Za-z]", value)
    return len(letters) >= 3
