"""Text model over any OpenAI-compatible /v1/chat/completions endpoint.

Works with Ollama (http://localhost:11434/v1), the official DeepSeek API
(https://api.deepseek.com/v1), and deepseek-bridge (http://127.0.0.1:11435/v1).
Images are not sent here; see ollama_vision.py.
"""
from __future__ import annotations

from collections.abc import Iterator

from ..config import TextModelSettings
from ..events import Target, TargetKind
from .prompts import SYSTEM, build_prompt


class OpenAICompatClient:
    def __init__(self, settings: TextModelSettings) -> None:
        from openai import OpenAI

        self._settings = settings
        self._client = OpenAI(base_url=settings.base_url, api_key=settings.api_key or "none", timeout=settings.timeout_s)

    def stream(self, kind: TargetKind, target: Target) -> Iterator[str]:
        max_tokens = self._settings.max_tokens_answer if kind in ("question", "code") else self._settings.max_tokens_summary
        response = self._client.chat.completions.create(
            model=self._settings.model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_prompt(kind, target)},
            ],
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
