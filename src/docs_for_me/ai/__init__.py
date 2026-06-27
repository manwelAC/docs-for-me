from docs_for_me.ai.base import AIProvider
from docs_for_me.ai.none import NoAIProvider
from docs_for_me.ai.opencode import OpenCodeProvider


def build_provider(name: str, model: str | None = None) -> AIProvider:
    normalized = name.strip().lower()

    if normalized in {"none", "no-ai", "off"}:
        return NoAIProvider()

    if normalized == "opencode":
        return OpenCodeProvider(model=model)

    raise ValueError(f"Unsupported AI provider: {name}")
