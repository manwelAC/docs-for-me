from dataclasses import dataclass
from typing import Callable


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class AIResponse:
    text: str
    used_ai: bool


class AIProvider:
    name = "base"

    def generate(
        self,
        prompt: str,
        files: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AIResponse:
        raise NotImplementedError
