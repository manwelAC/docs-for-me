from pathlib import Path

from docs_for_me.ai.base import AIProvider, ProgressCallback
from docs_for_me.core.content_signals import ContentSignals, analyze_content
from docs_for_me.core.language import detect_language
from docs_for_me.core.structure import summarize_structure
from docs_for_me.prompts import build_file_prompt


def document_file(path: Path, provider: AIProvider, on_progress: ProgressCallback | None = None) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    language = detect_language(path)
    structure = summarize_structure(content, language)
    signals = analyze_content(path, content, language)
    prompt = build_file_prompt(path, language, content, structure)
    ai_response = provider.generate(prompt, files=[str(path)], on_progress=on_progress)

    if ai_response.used_ai and ai_response.text:
        return ai_response.text

    return _fallback_file_doc(path, language, content, structure, signals, provider.name)


def _fallback_file_doc(
    path: Path,
    language: str,
    content: str,
    structure: list[str],
    signals: ContentSignals,
    provider_name: str,
) -> str:
    lines = content.splitlines()
    heading = path.name

    doc = [
        f"# {heading}",
        "",
        f"- **Path:** `{path}`",
        f"- **Language:** {language}",
        f"- **Lines:** {len(lines)}",
        f"- **AI:** unavailable or disabled (`{provider_name}`)",
        "",
        "## Overview",
        "",
        signals.purpose,
        "",
        f"**Confidence:** {signals.confidence}",
        "",
        "## What This Is Based On",
        "",
    ]

    doc.extend(f"- {item}" for item in signals.evidence)

    doc.extend([
        "",
        "## What Is Inside",
        "",
    ])

    doc.extend(f"- {item}" for item in _confirmed_facts(path, structure, signals))

    doc.extend([
        "",
        "## What It Does",
        "",
    ])

    doc.extend(f"- {item}" for item in _likely_facts(signals))

    doc.extend([
        "",
        "## Guide Notes",
        "",
    ])

    if signals.domain_terms:
        doc.append("- **Main concepts:** " + ", ".join(signals.domain_terms))
    if signals.actions:
        doc.append("- **Likely actions:** " + ", ".join(signals.actions))
    if signals.entities:
        doc.append("- **Data/entities:** " + ", ".join(signals.entities))
    if signals.labels:
        doc.append("- **Readable labels/text:** " + "; ".join(f"`{label}`" for label in signals.labels[:8]))
    if signals.endpoint_topics:
        doc.append("- **Endpoint topics:** " + ", ".join(signals.endpoint_topics[:8]))
    if signals.endpoints:
        doc.append("- **Paths or URLs:** " + "; ".join(f"`{endpoint}`" for endpoint in signals.endpoints[:8]))
    if signals.comments:
        doc.append("- **Comments:** " + "; ".join(f"`{comment}`" for comment in signals.comments[:4]))

    if not any([signals.domain_terms, signals.actions, signals.labels, signals.endpoints, signals.comments]):
        doc.append("- No strong content signals were detected.")

    doc.extend([
        "",
        "## Structure",
        "",
    ])

    if structure:
        doc.extend(f"- {item}" for item in structure)
    else:
        doc.append("- No obvious classes, functions, or imports were detected.")

    doc.extend(["", "## Reading Guide", "", "- Start with the overview, then use the structure section to find the main function, class, component, or data shape."])
    return "\n".join(doc) + "\n"


def _confirmed_facts(path: Path, structure: list[str], signals: ContentSignals) -> list[str]:
    facts = [f"Located at `{path}`."]

    functions = _names_for("function", structure)
    classes = _names_for("class", structure)
    interfaces = _names_for("interface", structure)

    if functions:
        facts.append("Main functions/components: " + ", ".join(f"`{name}`" for name in functions[:8]) + ".")
    if classes:
        facts.append("Classes: " + ", ".join(f"`{name}`" for name in classes[:8]) + ".")
    if interfaces:
        facts.append("Data shapes/interfaces: " + ", ".join(f"`{name}`" for name in interfaces[:8]) + ".")
    if signals.labels:
        facts.append("User-facing labels/statuses include " + ", ".join(f"`{label}`" for label in signals.labels[:6]) + ".")
    if signals.endpoints:
        topics = signals.endpoint_topics[:6] or signals.endpoints[:3]
        facts.append("Uses paths or endpoints related to " + ", ".join(topics) + ".")
    if signals.comments:
        facts.append("Code comments mention " + ", ".join(f"`{comment}`" for comment in signals.comments[:3]) + ".")

    return facts


def _likely_facts(signals: ContentSignals) -> list[str]:
    facts: list[str] = []

    if signals.entities:
        facts.append("The main data concepts appear to be " + ", ".join(signals.entities[:6]) + ".")
    elif signals.domain_terms:
        facts.append("The main concepts appear to be " + ", ".join(signals.domain_terms[:6]) + ".")

    if signals.actions:
        facts.append("The file likely supports actions such as " + ", ".join(signals.actions[:8]) + ".")

    if signals.endpoint_topics:
        facts.append("Its data/API usage appears connected to " + ", ".join(signals.endpoint_topics[:8]) + ".")

    if not facts:
        facts.append("There is not enough static evidence to infer behavior confidently.")

    return facts


def _names_for(label: str, structure: list[str]) -> list[str]:
    prefix = f"{label}: `"
    names: list[str] = []

    for item in structure:
        if not item.startswith(prefix):
            continue
        names.append(item.removeprefix(prefix).removesuffix("`"))

    return names
