from __future__ import annotations

from typing import Any

from llm.gemini_client import GeminiClient
from llm.prompt_builder import build_system_prompt, build_user_prompt


class GeminiAnalyst:
    def __init__(self, client: GeminiClient | None = None):
        self.client = client or GeminiClient()

    @property
    def is_configured(self) -> bool:
        return self.client.is_configured

    def answer(self, question: str, context: dict[str, Any]) -> str:
        return self.client.complete(
            system_prompt=build_system_prompt(),
            user_prompt=build_user_prompt(question=question, context=context),
        )
