from __future__ import annotations

from typing import Any

from backend_api.app.services.llm_router import router_completion


class _RouterChatCompletions:
    def __init__(self, locale: str = "zh") -> None:
        self._locale = locale

    def create(self, **kwargs: Any):
        messages = kwargs.pop("messages", None)
        if messages is None:
            raise ValueError("messages is required")
        call_kwargs = {
            "messages": messages,
            "response_format": kwargs.pop("response_format", None),
            "temperature": kwargs.pop("temperature", 0),
            "max_tokens": kwargs.pop("max_tokens", 800),
            "locale": kwargs.pop("locale", self._locale),
        }
        kwargs.pop("model", None)
        response, _model_name = router_completion(**call_kwargs)
        return response


class _RouterChat:
    def __init__(self, locale: str = "zh") -> None:
        self.completions = _RouterChatCompletions(locale=locale)


class OpenAI:
    """OpenAI-compatible shim backed by the unified LLM Router."""

    def __init__(self, *args: Any, locale: str = "zh", **kwargs: Any) -> None:
        self.chat = _RouterChat(locale=locale)
