from __future__ import annotations

from typing import Any

from llm.mistral_client import MistralClient
from llm.prompt_builder import build_system_prompt, build_user_prompt


class MistralAnalyst:
    def __init__(self, client: MistralClient | None = None):
        self.client = client or MistralClient()

    @property
    def is_configured(self) -> bool:
        return self.client.is_configured

    def answer(self, question: str, context: dict[str, Any]) -> str:
        return self.client.complete(
            system_prompt=build_system_prompt(),
            user_prompt=build_user_prompt(question=question, context=context),
        )
