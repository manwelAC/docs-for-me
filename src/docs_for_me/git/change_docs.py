from dataclasses import dataclass, field
import re
import tempfile
from pathlib import Path

from docs_for_me.ai.base import AIProvider, AIResponse, ProgressCallback
from docs_for_me.analyzer import ChangeSignal, detect_line_signals
from docs_for_me.git.diff_reader import read_diff
from docs_for_me.prompts import build_changes_prompt


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int = 0
    removed: int = 0
    added_hints: list[str] = field(default_factory=list)
    removed_hints: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    signals: list[ChangeSignal] = field(default_factory=list)


@dataclass(frozen=True)
class ChangePattern:
    name: str
    summary_phrase: str
    file_phrase: str
    commit_phrase: str
    area_phrase: str
    confidence: str = "Medium"


@dataclass(frozen=True)
class CommitMessage:
    subject: str
    body: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        if not self.body:
            return self.subject
        return "\n\n".join([self.subject, *self.body])


def document_changes(
    provider: AIProvider,
    staged: bool = False,
    since: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    if on_progress:
        on_progress("Reading Git diff...")
    diff = read_diff(staged=staged, since=since)
    prompt = build_changes_prompt(diff, staged=staged, since=since)
    ai_response = _generate_ai_changes(provider, prompt, diff, on_progress)

    if ai_response.used_ai and ai_response.text:
        return ai_response.text

    return _fallback_changes_doc(diff, provider.name, staged=staged, since=since, on_progress=on_progress)


def _generate_ai_changes(
    provider: AIProvider,
    prompt: str,
    diff: str,
    on_progress: ProgressCallback | None,
) -> AIResponse:
    if provider.name == "none" or not diff.strip():
        return provider.generate(prompt, on_progress=on_progress)

    with tempfile.TemporaryDirectory(prefix=".docs-for-me-", dir=Path.cwd()) as temp_dir:
        diff_path = Path(temp_dir) / "git-changes.diff"
        diff_path.write_text(diff, encoding="utf-8")
        return provider.generate(prompt, files=[str(diff_path)], on_progress=on_progress)


def _fallback_changes_doc(
    diff: str,
    provider_name: str,
    staged: bool,
    since: str | None,
    on_progress: ProgressCallback | None = None,
) -> str:
    title = "Git Changes"
    mode = f"since `{since}`" if since else "staged changes" if staged else "unstaged changes"

    if not diff.strip():
        return f"# {title}\n\nNo {mode} were found.\n"

    if on_progress:
        on_progress("Parsing changed files and changed lines...")
    changes = _parse_file_changes(diff, on_progress=on_progress)
    if on_progress:
        changed_lines = sum(change.added + change.removed for change in changes)
        signal_count = sum(len(change.signals) for change in changes)
        on_progress(f"Detected {changed_lines} changed line(s) across {len(changes)} file(s).")
        on_progress(f"Scoring {signal_count} local detector signal(s)...")
        on_progress("Rendering developer-readable Markdown...")
    added = sum(change.added for change in changes)
    removed = sum(change.removed for change in changes)
    files = [change.path for change in changes]
    commit_message = _suggest_commit_message(changes, added, removed)
    commit_text = commit_message.as_text()

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
        "## Changed Areas",
        "",
        *_changed_area_sections(changes),
        "",
        "## Commit Message",
        "",
        "Copy this into your commit command after you review the generated guide. You can delete this docs file afterward if it was only created for commit prep.",
        "",
        "```text",
        commit_text,
        "```",
        "",
        "Example:",
        "",
        "```powershell",
        _commit_command(commit_message),
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


def _suggest_commit_message(changes: list[FileChange], added: int, removed: int) -> CommitMessage:
    if not changes:
        return CommitMessage("chore: update project files")

    subject = _commit_subject(changes)
    has_behavior_theme = subject != _commit_scope(_change_topics(changes))

    if has_behavior_theme:
        verb = "update"
    elif added > 0 and removed == 0:
        verb = "add"
    elif removed > 0 and added == 0:
        verb = "remove"
    else:
        verb = "update"

    return CommitMessage(f"{verb}: {subject}", _commit_body(changes, added, removed))


def _commit_body(changes: list[FileChange], added: int, removed: int) -> list[str]:
    body: list[str] = []
    categories = _commit_categories(changes)

    for title in ["Added", "Updated", "Refactored", "Removed"]:
        items = categories.get(title, [])
        if items:
            body.append(_commit_section(title, items))

    files = [change.path for change in changes]
    if files:
        shown_files = ", ".join(files[:6])
        if len(files) > 6:
            shown_files += f", and {len(files) - 6} more"
        body.append(f"Affected files: {shown_files}.")

    changed_functions = _changed_functions(changes)
    if changed_functions:
        body.append(f"Visible changed areas: {_human_join(changed_functions[:8])}.")

    body.append(f"Diff size: {len(changes)} file(s), {added} added line(s), {removed} removed line(s).")
    return body


def _commit_categories(changes: list[FileChange]) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {
        "Added": [],
        "Updated": [],
        "Refactored": [],
        "Removed": [],
    }

    pattern_groups = _pattern_groups(changes)
    grouped_paths = {change.path for _, grouped_changes in pattern_groups for change in grouped_changes}

    for pattern, grouped_changes in pattern_groups:
        target = _domain_for_changes(grouped_changes) or "the affected files"
        title = "Refactored" if _pattern_is_refactor(pattern) else "Updated"
        categories[title].append(f"{target}: {pattern.file_phrase}.")

    for change in changes:
        if change.path in grouped_paths:
            continue
        target = _file_topic(change.path)
        concepts = _changed_concept_text(change)
        detail = f" around {concepts}" if concepts else ""

        if change.added and not change.removed:
            categories["Added"].append(f"{target}: added behavior or data{detail}.")
        elif change.removed and not change.added:
            categories["Removed"].append(f"{target}: removed behavior or data{detail}.")
        elif _looks_like_refactor(change):
            categories["Refactored"].append(f"{target}: reorganized existing behavior{detail}.")
        else:
            categories["Updated"].append(f"{target}: changed existing behavior{detail}.")

    return {title: _dedupe(items)[:6] for title, items in categories.items()}


def _commit_section(title: str, items: list[str]) -> str:
    return "\n".join([f"{title}:", *(f"- {item}" for item in items)])


def _pattern_is_refactor(pattern: ChangePattern) -> bool:
    return pattern.name in {"shared lookup behavior"}


def _looks_like_refactor(change: FileChange) -> bool:
    terms = _change_terms(change)
    refactor_terms = {"helper", "shared", "extract", "reuse", "rename", "move", "lookup"}
    return bool(terms & refactor_terms) and change.added > 0 and change.removed > 0


def _commit_command(message: CommitMessage) -> str:
    if not message.body:
        return f'git commit -m "{_escape_commit_arg(message.subject)}"'
    body = " ".join(message.body)
    return f'git commit -m "{_escape_commit_arg(message.subject)}" -m "{_escape_commit_arg(body)}"'


def _escape_commit_arg(value: str) -> str:
    return value.replace('"', '\\"')


def _commit_subject(changes: list[FileChange]) -> str:
    pattern = _dominant_pattern(changes)
    domain = _dominant_domain(changes)

    if pattern:
        if domain:
            return f"{pattern.commit_phrase} in {domain}"
        return pattern.commit_phrase

    topics = _change_topics(changes)
    return _commit_scope(topics)


def _changed_functions(changes: list[FileChange]) -> list[str]:
    names: list[str] = []
    for change in changes:
        for function in change.functions:
            names.append(f"{_file_topic(change.path)}::{function}")
    return _dedupe(names)


def _summarize_change(changes: list[FileChange], added: int, removed: int) -> str:
    if not changes:
        return "The diff changes project files, but no standard Git file headers were found."

    themes = _change_themes(changes)
    if themes:
        theme_text = " ".join(themes)
        return f"These changes update {len(changes)} file(s). {theme_text}"

    topics = _change_topics(changes)
    topic_text = ", ".join(topics[:5]) if topics else "project files"
    return f"These changes update {len(changes)} file(s), mainly around {topic_text}. The guide below summarizes the changed flow and the files involved."


def _change_sections(changes: list[FileChange]) -> list[str]:
    sections: list[str] = []

    for change in changes:
        sections.append(f"### `{change.path}`")
        sections.append("")
        sections.append(_describe_file_change(change))
        sections.append("")

    return sections


def _describe_file_change(change: FileChange) -> str:
    topic = _file_topic(change.path)
    pattern = _change_pattern(change)

    if pattern:
        sentences = [f"This file updates {topic}."]
        sentences.append(f"It {pattern.file_phrase}.")
        function_text = ", ".join(f"`{function}`" for function in change.functions[:4])
        if function_text:
            sentences.append(f"The changed code area includes {function_text}.")
        return " ".join(sentences)
    if change.functions:
        function_text = ", ".join(f"`{function}`" for function in change.functions[:4])
        story = _infer_change_story(change, topic)
        return f"{story} The visible changed area is {function_text}."

    if change.added and change.removed:
        return _infer_change_story(change, topic)
    if change.added:
        return _infer_added_story(change, topic)
    if change.removed:
        return _infer_removed_story(change, topic)
    return f"This file is listed in the diff, but no readable line-level changes were detected."


def _infer_change_story(change: FileChange, topic: str) -> str:
    terms = _change_terms(change)

    if _has_any(terms, {"query", "where", "wherein", "filter"}):
        return (
            f"This file changes how {topic} builds or applies its data filtering. "
            "The impact is that the returned records may now include a different set of results based on the updated filter rules."
        )
    if _has_any(terms, {"input", "search", "keydown", "enter", "draft"}):
        return (
            f"This file changes input or search handling in {topic}. "
            "The exact user-facing behavior should be reviewed in context, but the visible diff points to how values are edited or applied."
        )
    if _has_any(terms, {"markup", "style", "class", "classname", "layout"}):
        return (
            f"This file changes markup or presentation in {topic}. "
            "The visible diff mostly points to UI structure or styling rather than business logic."
        )

    if change.functions:
        function_text = ", ".join(f"`{function}`" for function in change.functions[:4])
        return (
            f"This file changes behavior in {topic}, mainly around {function_text}. "
            "The impact is local to the workflow handled by those changed functions."
        )

    concepts = _important_change_terms(terms)
    if concepts:
        concept_text = _human_join(concepts[:4])
        return (
            f"This file changes how {topic} handles {concept_text}. "
            "The impact is that this part of the flow may now make different decisions or return different results for those concepts."
        )

    return (
        f"This file changes behavior in {topic}. "
        "The impact is not specific enough to infer from static diff signals alone, but the file is part of the changed flow."
    )


def _infer_added_story(change: FileChange, topic: str) -> str:
    terms = _important_change_terms(_change_terms(change))
    if change.functions:
        return f"This file adds behavior in {topic}, including {_human_join(change.functions[:4])}."
    if terms:
        return f"This file adds behavior or data around {_human_join(terms[:4])} in {topic}."
    return f"This file adds new behavior around {topic}."


def _infer_removed_story(change: FileChange, topic: str) -> str:
    terms = _important_change_terms(_change_terms(change))
    if change.functions:
        return f"This file removes behavior in {topic}, including {_human_join(change.functions[:4])}."
    if terms:
        return f"This file removes behavior or data around {_human_join(terms[:4])} in {topic}."
    return f"This file removes behavior around {topic}."


def _changed_area_sections(changes: list[FileChange]) -> list[str]:
    sections: list[str] = []
    pattern_groups = _pattern_groups(changes)

    for pattern, grouped_changes in pattern_groups:
        sections.append(f"- {pattern.area_phrase}")
        sections.append("  Files: " + ", ".join(f"`{change.path}`" for change in grouped_changes[:8]))

    themed_paths = {change.path for _, grouped_changes in pattern_groups for change in grouped_changes}
    remaining = [change for change in changes if change.path not in themed_paths]
    for change in remaining[:8]:
        functions = ", ".join(f"`{function}`" for function in change.functions[:4])
        if functions:
            sections.append(f"- `{change.path}` updates {functions}: {_infer_change_story(change, _file_topic(change.path))}")
        else:
            sections.append(f"- `{change.path}`: {_infer_change_story(change, _file_topic(change.path))}")

    if not sections:
        sections.append("- No high-level change areas could be inferred from the diff, but the changed files are listed below.")

    return sections


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

    pattern = _dominant_pattern(changes)
    if pattern:
        topics.append(pattern.name)

    for change in changes:
        for topic in [_file_topic(change.path), *_topics_from_hints(change.added_hints)]:
            if topic and topic not in topics:
                topics.append(topic)

    return topics


def _commit_scope(topics: list[str]) -> str:
    filtered = [topic for topic in topics if topic not in {"page", "app", "line", "changed"}]
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
        if part.startswith("(") and part.endswith(")"):
            continue
        stem = part.rsplit(".", 1)[0].strip("()[]{}")
        if stem in {"app", "src", "page", "index", "layout"}:
            continue
        words = _humanize_identifier(stem)
        if len(words) >= 3:
            meaningful.append(words)

    return meaningful[-1] if meaningful else "this area"


def _humanize_identifier(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


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
                "classname",
                "import",
                "export",
                "true",
                "false",
                "line",
                "changed",
                "value",
                "text",
                "behavior",
                "binding",
                "input",
                "local",
                "markup",
                "presentation",
                "state",
            }:
                continue
            if cleaned not in topics:
                topics.append(cleaned)
            if len(topics) >= 4:
                return topics

    return topics


def _change_terms(change: FileChange) -> set[str]:
    text = " ".join([*change.added_hints, *change.removed_hints, *change.functions]).lower()
    return {
        word.replace("-", "_")
        for word in re.findall(r"[A-Za-z_][A-Za-z0-9_-]{2,}", text)
        if word.lower() not in {
            "line",
            "changed",
            "text",
            "value",
            "behavior",
            "binding",
            "class",
            "classname",
            "code",
            "const",
            "draft",
            "event",
            "input",
            "local",
            "markup",
            "presentation",
            "state",
            "style",
            "true",
            "false",
            "null",
            "return",
            "public",
            "private",
            "protected",
        }
    }


def _has_any(terms: set[str], expected: set[str]) -> bool:
    return bool(terms & expected)


def _important_change_terms(terms: set[str]) -> list[str]:
    ignored = {
        "action",
        "behavior",
        "bg",
        "class",
        "classname",
        "cleartimeout",
        "commitsearch",
        "const",
        "div",
        "draft",
        "event",
        "input",
        "line",
        "local",
        "markup",
        "presentation",
        "query",
        "search",
        "set",
        "state",
        "style",
        "text",
        "use",
        "value",
        "where",
        "wherein",
        "this",
        "that",
        "with",
        "from",
        "code",
        "area",
    }
    return sorted(term.replace("_", " ") for term in terms if term not in ignored)[:8]


def _human_join(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _change_pattern(change: FileChange) -> ChangePattern | None:
    signals = _change_signals(change)
    if not signals:
        return None

    family = _dominant_signal_family(signals)
    if _signal_family_score(signals, family) < 0.65:
        return None
    evidence = _signal_evidence_phrase(signals, family)
    confidence = _signal_confidence(signals, family)
    label = family.replace("_", " ")

    return ChangePattern(
        name=f"{family} change",
        summary_phrase=_compose_summary_phrase(label, evidence, confidence),
        file_phrase=_compose_file_phrase(label, evidence),
        commit_phrase=_compose_commit_phrase(label, evidence),
        area_phrase=_compose_area_phrase(label, evidence, confidence),
        confidence=confidence,
    )


def _change_signals(change: FileChange) -> list[ChangeSignal]:
    return change.signals


def _dominant_signal_family(signals: list[ChangeSignal]) -> str:
    scores: dict[str, float] = {}

    for signal in signals:
        scores[signal.family] = scores.get(signal.family, 0.0) + _signal_weight(signal)

    return max(scores.items(), key=lambda item: item[1])[0]


def _signal_family_score(signals: list[ChangeSignal], family: str) -> float:
    return sum(_signal_weight(signal) for signal in signals if signal.family == family)


def _signal_weight(signal: ChangeSignal) -> float:
    evidence = signal.evidence.lower()

    if signal.side == "added":
        weight = signal.confidence
    else:
        weight = signal.confidence * 0.7

    if any(term in evidence for term in ["grouped", "direct", "binding", "handler", "editable", "status"]):
        weight += 0.4
    if any(term in evidence for term in ["markup", "presentation", "styling"]):
        weight -= 0.2

    return weight


def _signal_evidence_phrase(signals: list[ChangeSignal], family: str) -> str:
    family_signals = [signal for signal in signals if signal.family == family]
    added = _dedupe([signal.evidence.lower() for signal in family_signals if signal.side == "added"])
    removed = _dedupe([signal.evidence.lower() for signal in family_signals if signal.side == "removed"])
    common = set(added) & set(removed)
    added_only = [item for item in added if item not in common]
    removed_only = [item for item in removed if item not in common]

    if added_only and removed_only:
        return f"from {_human_join(removed_only[:2])} to {_human_join(added_only[:2])}"
    if added_only:
        return _human_join(added_only[:3])
    if removed_only:
        return f"removed {_human_join(removed_only[:3])}"
    if added:
        return _human_join(added[:3])
    if removed:
        return _human_join(removed[:3])
    return "visible diff signals changed"


def _signal_confidence(signals: list[ChangeSignal], family: str) -> str:
    family_signals = [signal for signal in signals if signal.family == family]
    added = {signal.evidence.lower() for signal in family_signals if signal.side == "added"}
    removed = {signal.evidence.lower() for signal in family_signals if signal.side == "removed"}

    if added and removed:
        return "High"
    if len(added) + len(removed) >= 2:
        return "Medium"
    return "Low"


def _compose_summary_phrase(label: str, evidence: str, confidence: str) -> str:
    if evidence == label:
        return f"{label.title()} changed."
    if evidence.startswith("from "):
        return f"{label.title()} changed {evidence}."
    if evidence.startswith("removed "):
        return f"{label.title()} {evidence}."
    return f"{label.title()} changed around {evidence}."


def _compose_file_phrase(label: str, evidence: str) -> str:
    if evidence == label:
        return f"updates {label}"
    if evidence.startswith("from "):
        return f"updates {label} {evidence}"
    if evidence.startswith("removed "):
        return f"{evidence} from {label}"
    return f"updates {label} around {evidence}"


def _compose_commit_phrase(label: str, evidence: str) -> str:
    return f"update {label}"


def _compose_area_phrase(label: str, evidence: str, confidence: str) -> str:
    if evidence == label:
        return f"{label.title()} areas changed."
    if evidence.startswith("from "):
        return f"{label.title()} areas changed {evidence}."
    if evidence.startswith("removed "):
        return f"{label.title()} areas {evidence}."
    return f"{label.title()} areas changed around {evidence}."


def _dominant_pattern(changes: list[FileChange]) -> ChangePattern | None:
    patterns = [_change_pattern(change) for change in changes]
    patterns = [pattern for pattern in patterns if pattern is not None]
    if not patterns:
        return None

    counts: dict[str, tuple[ChangePattern, int]] = {}
    for pattern in patterns:
        _, count = counts.get(pattern.name, (pattern, 0))
        counts[pattern.name] = (pattern, count + 1)

    return max(counts.values(), key=lambda item: item[1])[0]


def _pattern_groups(changes: list[FileChange]) -> list[tuple[ChangePattern, list[FileChange]]]:
    groups: dict[str, tuple[ChangePattern, list[FileChange]]] = {}
    for change in changes:
        pattern = _change_pattern(change)
        if pattern is None:
            continue
        stored_pattern, stored_changes = groups.get(pattern.name, (pattern, []))
        stored_changes.append(change)
        groups[pattern.name] = (stored_pattern, stored_changes)
    return list(groups.values())


def _dominant_domain(changes: list[FileChange]) -> str:
    pattern = _dominant_pattern(changes)
    scoped_changes = [change for change in changes if _change_pattern(change) == pattern] if pattern else changes
    scoped_changes = scoped_changes or changes
    return _domain_for_changes(scoped_changes)


def _domain_for_changes(changes: list[FileChange]) -> str:
    common_role = _common_path_role(changes)
    topics = _dedupe([_file_topic(change.path) for change in changes if _file_topic(change.path) != "this area"])

    if len(changes) >= 4 and common_role:
        return common_role
    if len(topics) == 1:
        return topics[0]
    if len(topics) == 2:
        return f"{topics[0]} and {topics[1]}"
    if len(topics) > 2 and common_role:
        return common_role
    if topics:
        return "changed flows"
    return ""


def _common_path_role(changes: list[FileChange]) -> str:
    role_counts: dict[str, int] = {}
    for change in changes:
        parts = [part.lower() for part in change.path.replace("\\", "/").split("/")[:-1]]
        for part in parts:
            if part.startswith("(") and part.endswith(")"):
                continue
            readable = _humanize_identifier(part)
            if readable in {"app", "src", "http", "api"} or len(readable) < 3:
                continue
            role_counts[readable] = role_counts.get(readable, 0) + 1
    if not role_counts:
        return ""
    role, count = max(role_counts.items(), key=lambda item: item[1])
    if count < 2:
        return ""
    return f"changed {role}"


def _changed_concept_text(change: FileChange) -> str:
    concepts = _important_change_terms(_change_terms(change))
    return _human_join(concepts[:4])


def _visible_evidence_text(change: FileChange) -> str:
    primary_family = _dominant_signal_family(change.signals) if change.signals else ""
    evidence = [
        signal.evidence.lower()
        for signal in change.signals
        if signal.family == primary_family or (signal.confidence >= 0.65 and signal.detector != "path_pattern")
    ]

    if change.functions:
        evidence.extend(f"`{function}`" for function in change.functions[:3])

    return _human_join(_dedupe(evidence)[:4])


def _change_themes(changes: list[FileChange]) -> list[str]:
    themes: list[str] = []

    pattern_groups = _pattern_groups(changes)
    for pattern, grouped_changes in pattern_groups:
        topics = ", ".join(_file_topic(change.path) for change in grouped_changes[:6])
        themes.append(f"{pattern.summary_phrase} Affected areas include {topics}.")

    themed_paths = {change.path for _, grouped_changes in pattern_groups for change in grouped_changes}
    remaining = len([change for change in changes if change.path not in themed_paths])
    if remaining > 0:
        themes.append(f"{remaining} other file(s) include smaller behavior updates.")

    return themes


def _parse_file_changes(diff: str, on_progress: ProgressCallback | None = None) -> list[FileChange]:
    changes: list[FileChange] = []
    current_path: str | None = None
    added = 0
    removed = 0
    added_hints: list[str] = []
    removed_hints: list[str] = []
    functions: list[str] = []
    signals: list[ChangeSignal] = []
    detected_files = 0

    def flush() -> None:
        nonlocal current_path, added, removed, added_hints, removed_hints, functions, signals
        if current_path is not None:
            changes.append(
                FileChange(
                    path=current_path,
                    added=added,
                    removed=removed,
                    added_hints=added_hints[:8],
                    removed_hints=removed_hints[:6],
                    functions=_dedupe(functions)[:8],
                    signals=_dedupe_signals(signals),
                )
            )
        current_path = None
        added = 0
        removed = 0
        added_hints = []
        removed_hints = []
        functions = []
        signals = []

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            parts = line.split()
            current_path = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else parts[-1]
            detected_files += 1
            if on_progress:
                on_progress(f"Analyzing changed file {detected_files}: {current_path}")
            continue

        if current_path is None:
            continue

        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            line_signals = detect_line_signals(current_path, line[1:], "added")
            added += 1
            functions.extend(_function_names_from_line(line[1:]))
            signals.extend(line_signals)
            added_hints.extend(signal.as_hint() for signal in line_signals)
            hint = _readable_change_hint(line[1:])
            if hint:
                added_hints.append(hint)
        elif line.startswith("-"):
            line_signals = detect_line_signals(current_path, line[1:], "removed")
            removed += 1
            functions.extend(_function_names_from_line(line[1:]))
            signals.extend(line_signals)
            removed_hints.extend(signal.as_hint() for signal in line_signals)
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
    if function_match and not re.search(r"\buse[A-Z][A-Za-z0-9_]*\s*\(", stripped):
        return f"Code area: `{function_match.group(1)}`"

    return f"Line changed: `{stripped}`"


def _function_names_from_line(line: str) -> list[str]:
    names: list[str] = []
    patterns = [
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b(?:public|private|protected)\s+function\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, line):
            names.append(match.group(1))
    return names


def _looks_readable(value: str) -> bool:
    if value.startswith(("@/", "./", "../", "http://", "https://")):
        return False
    letters = re.findall(r"[A-Za-z]", value)
    return len(letters) >= 3


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _dedupe_signals(signals: list[ChangeSignal]) -> list[ChangeSignal]:
    seen = set()
    deduped: list[ChangeSignal] = []

    for signal in signals:
        key = (signal.family, signal.evidence, signal.side, signal.detector)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(signal)

    return deduped
