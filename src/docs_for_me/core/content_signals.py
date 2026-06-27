import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


STOP_WORDS = {
    "about",
    "after",
    "again",
    "all",
    "also",
    "and",
    "any",
    "api",
    "app",
    "are",
    "async",
    "await",
    "background",
    "border",
    "bold",
    "but",
    "button",
    "can",
    "card",
    "class",
    "classname",
    "content",
    "const",
    "center",
    "def",
    "dialog",
    "div",
    "else",
    "emerald",
    "export",
    "false",
    "fetch",
    "flex",
    "focus",
    "font",
    "for",
    "from",
    "function",
    "full",
    "gap",
    "get",
    "has",
    "have",
    "import",
    "into",
    "items",
    "justify",
    "json",
    "label",
    "layout",
    "let",
    "link",
    "loading",
    "mono",
    "name",
    "new",
    "not",
    "null",
    "opacity",
    "out",
    "page",
    "px",
    "py",
    "react",
    "rounded",
    "return",
    "selected",
    "semibold",
    "set",
    "size",
    "space",
    "span",
    "state",
    "string",
    "text",
    "that",
    "the",
    "this",
    "true",
    "type",
    "tsx",
    "use",
    "value",
    "var",
    "white",
    "with",
    "your",
    "zinc",
}

HTML_TAGS = {
    "a",
    "article",
    "aside",
    "body",
    "button",
    "div",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "head",
    "header",
    "html",
    "img",
    "input",
    "label",
    "li",
    "link",
    "main",
    "nav",
    "option",
    "p",
    "section",
    "select",
    "span",
    "table",
    "tbody",
    "td",
    "textarea",
    "th",
    "thead",
    "tr",
    "ul",
}

ACTION_WORDS = {
    "add",
    "approve",
    "book",
    "cancel",
    "change",
    "check",
    "create",
    "delete",
    "edit",
    "export",
    "filter",
    "find",
    "generate",
    "import",
    "load",
    "login",
    "logout",
    "manage",
    "pay",
    "print",
    "read",
    "register",
    "remove",
    "render",
    "save",
    "search",
    "select",
    "send",
    "show",
    "submit",
    "sync",
    "update",
    "upload",
    "validate",
    "view",
    "write",
}


@dataclass(frozen=True)
class ContentSignals:
    purpose: str
    domain_terms: list[str]
    actions: list[str]
    labels: list[str]
    endpoints: list[str]
    endpoint_topics: list[str]
    entities: list[str]
    comments: list[str]
    evidence: list[str] = field(default_factory=list)
    confidence: str = "Low"


def analyze_content(path: Path, content: str, language: str) -> ContentSignals:
    words = extract_path_terms(path) + _split_identifier_words(content)
    domain_terms = _top_domain_terms(words)
    actions = _top_actions(words)
    labels = _extract_string_literals(content)
    endpoints = _extract_paths_and_urls(content)
    endpoint_topics = _endpoint_topics(endpoints)
    entities = _extract_entities(content)
    comments = _extract_comments(content, language)
    purpose = _infer_purpose(path, domain_terms, actions, labels)
    evidence = _build_evidence(path, domain_terms, actions, labels, endpoints, endpoint_topics, entities, comments)
    confidence = _confidence_for(evidence)

    return ContentSignals(
        purpose=purpose,
        domain_terms=domain_terms,
        actions=actions,
        labels=labels,
        endpoints=endpoints,
        endpoint_topics=endpoint_topics,
        entities=entities,
        comments=comments,
        evidence=evidence,
        confidence=confidence,
    )


def extract_path_terms(path: Path) -> list[str]:
    words: list[str] = []
    for part in path.parts:
        clean_part = part.strip("()[]{}")
        words.extend(_split_token(clean_part))
    return words


def _split_identifier_words(content: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", content)
    words: list[str] = []
    for token in tokens:
        words.extend(_split_token(token))
    return words


def _split_token(token: str) -> list[str]:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", normalized)
    return [word.lower() for word in normalized.split() if _is_meaningful_word(word)]


def _is_meaningful_word(word: str) -> bool:
    return len(word) > 2 and word.lower() not in STOP_WORDS and not word.isdigit()


def _top_domain_terms(words: list[str], limit: int = 12) -> list[str]:
    counts = Counter(word for word in words if word not in ACTION_WORDS)
    return [word for word, _count in counts.most_common(limit)]


def _top_actions(words: list[str], limit: int = 10) -> list[str]:
    counts = Counter(word for word in words if word in ACTION_WORDS)
    return [word for word, _count in counts.most_common(limit)]


def _extract_string_literals(content: str, limit: int = 12) -> list[str]:
    values: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) or re.search(r"\bfrom\s+['\"]", stripped):
            continue

        matches = re.findall(r"""(?:"([^"\n]{3,80})"|'([^'\n]{3,80})'|`([^`\n]{3,80})`)""", line)
        for groups in matches:
            value = next((group for group in groups if group), "").strip()
            if not _looks_like_human_label(value):
                continue
            if value not in values:
                values.append(value)
            if len(values) >= limit:
                return values

    return values


def _looks_like_human_label(value: str) -> bool:
    if "@" in value:
        return False
    if value.startswith(("@/", "./", "../", "http://", "https://")):
        return False
    if value in {"use client", "use strict"}:
        return False
    if value.islower() and re.fullmatch(r"[a-z0-9_.-]+", value):
        return False
    if re.search(r"\b(?:text|bg|border|rounded|hover|focus|px|py|mt|mb|ml|mr|flex|grid)-", value):
        return False
    if re.search(r"[{};=<>]", value):
        return False
    letters = re.findall(r"[A-Za-z]", value)
    return len(letters) >= 3


def _extract_paths_and_urls(content: str, limit: int = 12) -> list[str]:
    seen: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) or re.search(r"\bfrom\s+['\"]", stripped):
            continue

        matches = re.findall(r"""(?:https?://[^\s"'`<>]+|/[A-Za-z0-9_./{}[\]$:-]+)""", line)
        for match in matches:
            cleaned = match.rstrip(".,);")
            if cleaned == "//" or cleaned in {"/}", "/json"}:
                continue
            if re.fullmatch(r"/[-\dA-Za-z]+", cleaned):
                continue
            if _looks_like_markup_path(cleaned):
                continue
            if _looks_like_component_path(cleaned):
                continue
            if cleaned not in seen:
                seen.append(cleaned)
            if len(seen) >= limit:
                return seen

    return seen


def _looks_like_markup_path(value: str) -> bool:
    tag = value.lstrip("/").split("/", 1)[0].lower()
    return tag in HTML_TAGS


def _looks_like_component_path(value: str) -> bool:
    stripped = value.lstrip("/")
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9_]*", stripped))


def _endpoint_topics(endpoints: list[str], limit: int = 10) -> list[str]:
    topics: list[str] = []

    for endpoint in endpoints:
        for segment in re.split(r"[/?#&=.]+", endpoint):
            cleaned = segment.strip("{}[]:$").lower()
            if not _is_meaningful_word(cleaned):
                continue
            if cleaned in {"localhost", "http", "https", "api", "orgid", "hotelid", "selected", "id"}:
                continue
            if "localhost" in cleaned or re.fullmatch(r"\d+", cleaned):
                continue
            if cleaned not in topics:
                topics.append(cleaned)
            if len(topics) >= limit:
                return topics

    return topics


def _extract_entities(content: str, limit: int = 12) -> list[str]:
    patterns = [
        re.compile(r"^\s*(?:export\s+)?interface\s+([A-Z][A-Za-z0-9_]*)", re.MULTILINE),
        re.compile(r"^\s*(?:export\s+)?type\s+([A-Z][A-Za-z0-9_]*)", re.MULTILINE),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Z][A-Za-z0-9_]*)", re.MULTILINE),
        re.compile(r"\bstruct\s+([A-Z][A-Za-z0-9_]*)", re.MULTILINE),
    ]
    entities: list[str] = []

    for pattern in patterns:
        for match in pattern.finditer(content):
            entity = _humanize_identifier(match.group(1))
            if entity not in entities:
                entities.append(entity)
            if len(entities) >= limit:
                return entities

    return entities


def _extract_comments(content: str, language: str, limit: int = 8) -> list[str]:
    patterns = [
        re.compile(r"^\s*#\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*//\s+(.+)$", re.MULTILINE),
        re.compile(r"/\*\s*(.+?)\s*\*/", re.DOTALL),
    ]
    comments: list[str] = []

    for pattern in patterns:
        for match in pattern.finditer(content):
            comment = re.sub(r"\s+", " ", match.group(1)).strip()
            if len(comment) < 4:
                continue
            if _symbol_ratio(comment) > 0.35:
                continue
            comments.append(comment[:160])
            if len(comments) >= limit:
                return comments

    return comments


def _symbol_ratio(value: str) -> float:
    if not value:
        return 1.0
    symbol_count = sum(1 for char in value if not char.isalnum() and not char.isspace())
    return symbol_count / len(value)


def _infer_purpose(path: Path, domain_terms: list[str], actions: list[str], labels: list[str]) -> str:
    path_terms = extract_path_terms(path)
    strongest_terms = _dedupe(path_terms + domain_terms)[:5]
    strongest_actions = actions[:4]

    if not strongest_terms:
        return "This file appears to contain implementation details, but there were not enough readable signals to infer a specific purpose."

    subject = _human_join(strongest_terms)

    if strongest_actions:
        action_text = _human_join(strongest_actions)
        return f"This file appears to focus on {subject}. It likely supports actions such as {action_text}."

    if labels:
        return f"This file appears to focus on {subject}. Its readable text suggests user-facing content or configuration around those concepts."

    return f"This file appears to focus on {subject}."


def _build_evidence(
    path: Path,
    domain_terms: list[str],
    actions: list[str],
    labels: list[str],
    endpoints: list[str],
    endpoint_topics: list[str],
    entities: list[str],
    comments: list[str],
) -> list[str]:
    evidence = [f"Path/name signals: `{path}`"]

    if domain_terms:
        evidence.append("Repeated domain terms: " + ", ".join(domain_terms[:8]))
    if actions:
        evidence.append("Action words: " + ", ".join(actions[:8]))
    if labels:
        evidence.append("Readable labels/text: " + "; ".join(f"`{label}`" for label in labels[:5]))
    if endpoints:
        evidence.append("Paths or URLs: " + "; ".join(f"`{endpoint}`" for endpoint in endpoints[:5]))
    if endpoint_topics:
        evidence.append("Endpoint topics: " + ", ".join(endpoint_topics[:8]))
    if entities:
        evidence.append("Data/entities: " + ", ".join(entities[:8]))
    if comments:
        evidence.append("Comments: " + "; ".join(f"`{comment}`" for comment in comments[:3]))

    return evidence


def _confidence_for(evidence: list[str]) -> str:
    signal_count = max(0, len(evidence) - 1)
    if signal_count >= 4:
        return "High"
    if signal_count >= 2:
        return "Medium"
    return "Low"


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _human_join(values: list[str]) -> str:
    readable = [value.replace("_", " ") for value in values]
    if len(readable) == 1:
        return readable[0]
    if len(readable) == 2:
        return f"{readable[0]} and {readable[1]}"
    return ", ".join(readable[:-1]) + f", and {readable[-1]}"


def _humanize_identifier(value: str) -> str:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return normalized.lower()
