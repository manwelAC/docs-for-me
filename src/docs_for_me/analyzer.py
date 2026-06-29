from dataclasses import dataclass
from pathlib import PurePath
import re


@dataclass(frozen=True)
class ChangedLine:
    path: str
    text: str
    side: str


@dataclass(frozen=True)
class ChangeSignal:
    family: str
    evidence: str
    side: str
    detector: str
    confidence: float = 0.5

    def as_hint(self) -> str:
        label = self.family.replace("_", " ").title()
        return f"{label} behavior: {self.evidence}"


def detect_line_signals(path: str, text: str, side: str) -> list[ChangeSignal]:
    line = ChangedLine(path=path, text=text, side=side)
    signals: list[ChangeSignal] = []

    for detector in DETECTORS:
        signals.extend(detector(line))

    return signals


def detect_path_patterns(line: ChangedLine) -> list[ChangeSignal]:
    parts = [part.lower() for part in _path_parts(line.path)]
    name = _filename(line.path).lower()
    ext = _extension(line.path)
    signals: list[ChangeSignal] = []

    if any(part in {"test", "tests", "__tests__", "spec", "specs"} for part in parts) or ".test." in name or ".spec." in name:
        signals.append(ChangeSignal("test", "test file path", line.side, "path_pattern", 0.7))

    if name in {"package.json", "composer.json", "pyproject.toml", "go.mod", "cargo.toml"}:
        signals.append(ChangeSignal("manifest", "project manifest file", line.side, "path_pattern", 0.45))

    if ext in {".json", ".toml", ".yaml", ".yml", ".ini", ".env"} or name.endswith(".config.js") or name.endswith(".config.ts"):
        signals.append(ChangeSignal("config", "configuration file path", line.side, "path_pattern", 0.35))

    if name in {"page.tsx", "page.jsx", "page.js", "page.ts", "route.ts", "route.js", "index.html"}:
        signals.append(ChangeSignal("route", "entry-like file name", line.side, "path_pattern", 0.3))

    return signals


def detect_imports_exports(line: ChangedLine) -> list[ChangeSignal]:
    text = line.text.strip()
    signals: list[ChangeSignal] = []

    if re.match(r"(import|from)\s+", text) or "#include" in text or re.match(r"use\s+[\w:]+", text):
        signals.append(ChangeSignal("dependency", "import or include", line.side, "import_export", 0.65))

    if re.search(r"\bexport\b", text) or re.match(r"\s*(public|private|protected)?\s*(class|interface|struct|enum)\b", text):
        signals.append(ChangeSignal("api_surface", "exported symbol", line.side, "import_export", 0.65))

    return signals


def detect_symbols(line: ChangedLine) -> list[ChangeSignal]:
    if re.search(r"\buse[A-Z][A-Za-z0-9_]*\s*\(", line.text):
        return []

    patterns = [
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b(?:public|private|protected)\s+function\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"\bfunc\s+([A-Za-z_][A-Za-z0-9_]*)",
    ]
    signals: list[ChangeSignal] = []

    for pattern in patterns:
        for match in re.finditer(pattern, line.text):
            signals.append(ChangeSignal("symbol", f"symbol {_split_identifier(match.group(1))}", line.side, "symbol", 0.55))

    return signals


def detect_routes(line: ChangedLine) -> list[ChangeSignal]:
    text = line.text
    signals: list[ChangeSignal] = []

    if re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\b", text) and re.search(r"['\"]/", text):
        signals.append(ChangeSignal("route", "http route declaration", line.side, "route", 0.75))

    if re.search(r"['\"]/[A-Za-z0-9_./{}:$-]+['\"]", text):
        signals.append(ChangeSignal("route", "path-like string", line.side, "route", 0.45))

    return signals


def detect_dependencies(line: ChangedLine) -> list[ChangeSignal]:
    name = _filename(line.path).lower()
    text = line.text.strip()

    if name not in {"package.json", "composer.json", "pyproject.toml", "go.mod", "cargo.toml"}:
        return []

    if re.search(r"[A-Za-z0-9_.@/-]+\s*[:=]\s*['\"]?[\^~<>=0-9.*x-]", text):
        return [ChangeSignal("dependency", "dependency or version entry", line.side, "dependency", 0.75)]

    return []


def detect_tests(line: ChangedLine) -> list[ChangeSignal]:
    parts = [part.lower() for part in _path_parts(line.path)]
    name = _filename(line.path).lower()
    is_test_path = (
        any(part in {"test", "tests", "__tests__", "spec", "specs"} for part in parts)
        or ".test." in name
        or ".spec." in name
    )
    if not is_test_path:
        return []

    if re.search(r"\b(describe|it|test|expect|assert|should)\b", line.text):
        return [ChangeSignal("test", "test assertion or case", line.side, "test", 0.7)]
    return []


def detect_config(line: ChangedLine) -> list[ChangeSignal]:
    name = _filename(line.path).lower()
    ext = _extension(line.path)
    text = line.text.strip()

    is_config_path = (
        ext in {".json", ".toml", ".yaml", ".yml", ".ini", ".env"}
        or name.endswith(".config.js")
        or name.endswith(".config.ts")
    )
    if not is_config_path:
        return []

    if re.search(r"\b[A-Z][A-Z0-9_]{2,}\b\s*=", text):
        return [ChangeSignal("config", "environment-style setting", line.side, "config", 0.7)]

    if re.search(r"['\"]?[A-Za-z0-9_.-]+['\"]?\s*[:=]\s*['\"]?[^,'\"]+", text):
        return [ChangeSignal("config", "key value setting", line.side, "config", 0.45)]

    return []


def detect_ui_markup(line: ChangedLine) -> list[ChangeSignal]:
    text = line.text
    lowered = text.lower()
    signals: list[ChangeSignal] = []

    if re.search(r"</?[A-Za-z][A-Za-z0-9-]*", text):
        signals.append(ChangeSignal("markup", "markup", line.side, "ui_markup", 0.65))

    if re.search(r"\bclassName\s*=", text) or re.search(r"\bclass\s*=", text):
        signals.append(ChangeSignal("presentation", "styling or class binding", line.side, "ui_markup", 0.65))

    if re.search(r"\bvalue\s*=", text) or re.search(r"\bonChange\s*=", text):
        signals.append(ChangeSignal("input", "input binding", line.side, "ui_markup", 0.7))

    if "enter" in lowered and ("key" in lowered or "keydown" in lowered):
        signals.append(ChangeSignal("input", "keyboard apply handler", line.side, "ui_markup", 0.75))

    if ("search" in lowered and "input" in lowered) or "draft" in lowered:
        signals.append(ChangeSignal("input", "separate editable value", line.side, "ui_markup", 0.75))

    if re.search(r"\buse[A-Z][A-Za-z0-9_]*\s*\(", text) or re.search(r"\bset[A-Z][A-Za-z0-9_]*\s*\(", text):
        signals.append(ChangeSignal("ui_state", "local state", line.side, "ui_markup", 0.55))

    return signals


def detect_data_access(line: ChangedLine) -> list[ChangeSignal]:
    lowered = line.text.lower()
    signals: list[ChangeSignal] = []

    if "wherein" in lowered or re.search(r"\bwhere_in\b", lowered):
        signals.append(ChangeSignal("filtering", "grouped matching with wherein", line.side, "data_access", 0.8))
    elif "where(" in lowered or re.search(r"\bwhere\b", lowered):
        signals.append(ChangeSignal("filtering", "direct matching with where", line.side, "data_access", 0.75))

    if re.search(r"\b(select|insert|update|delete)\b", lowered) and re.search(r"\b(from|into|set|where)\b", lowered):
        signals.append(ChangeSignal("data_access", "query operation", line.side, "data_access", 0.65))

    if re.search(r"\b(filter|map|reduce|find|sort)\s*\(", line.text):
        signals.append(ChangeSignal("collection", "collection operation", line.side, "data_access", 0.55))

    return signals


def detect_network_calls(line: ChangedLine) -> list[ChangeSignal]:
    name = _filename(line.path).lower()
    if name.endswith(".lock"):
        return []

    if re.search(r"\b(fetch|axios|request|http)\b", line.text, flags=re.IGNORECASE) and re.search(r"['\"](?:https?://|/)", line.text):
        return [ChangeSignal("network", "network call", line.side, "network_call", 0.75)]
    return []


DETECTORS = [
    detect_path_patterns,
    detect_imports_exports,
    detect_symbols,
    detect_routes,
    detect_dependencies,
    detect_tests,
    detect_config,
    detect_ui_markup,
    detect_data_access,
    detect_network_calls,
]


def _path_parts(path: str) -> list[str]:
    return [part for part in PurePath(path.replace("\\", "/")).parts if part not in {"/", ""}]


def _filename(path: str) -> str:
    parts = _path_parts(path)
    return parts[-1] if parts else path


def _extension(path: str) -> str:
    name = _filename(path)
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def _split_identifier(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()
