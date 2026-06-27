from docs_for_me.ai.base import AIProvider, AIResponse, ProgressCallback


class NoAIProvider(AIProvider):
    name = "none"

    def generate(
        self,
        prompt: str,
        files: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AIResponse:
        return AIResponse(text="", used_ai=False)
