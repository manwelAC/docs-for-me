import re


PATTERNS_BY_LANGUAGE = {
    "Python": [
        ("class", re.compile(r"^\s*class\s+([A-Za-z_][\w]*)", re.MULTILINE)),
        ("function", re.compile(r"^\s*def\s+([A-Za-z_][\w]*)", re.MULTILINE)),
        ("import", re.compile(r"^\s*(?:from\s+[\w.]+\s+import|import\s+.+)", re.MULTILINE)),
    ],
    "JavaScript": [
        ("class", re.compile(r"^\s*class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        (
            "function",
            re.compile(r"^\s*(?:export\s+)?(?:default\s+)?function\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
        ),
        ("import", re.compile(r"^\s*import\s+.+", re.MULTILINE)),
    ],
    "TypeScript": [
        ("class", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        (
            "function",
            re.compile(r"^\s*(?:export\s+)?(?:default\s+)?function\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
        ),
        ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
        ("import", re.compile(r"^\s*import\s+.+", re.MULTILINE)),
    ],
}


LANGUAGE_PATTERN_ALIASES = {
    "JavaScript React": "JavaScript",
    "TypeScript React": "TypeScript",
}


def summarize_structure(content: str, language: str) -> list[str]:
    pattern_language = LANGUAGE_PATTERN_ALIASES.get(language, language)
    patterns = PATTERNS_BY_LANGUAGE.get(pattern_language, [])
    found: list[str] = []

    for label, pattern in patterns:
        for match in pattern.finditer(content):
            name = match.group(1) if match.groups() else match.group(0).strip()
            if label == "import" and name.rstrip().endswith("{"):
                continue
            found.append(f"{label}: `{name}`")

    return found[:50]
