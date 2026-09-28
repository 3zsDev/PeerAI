"""Image targets go to a local Ollama vision model with the screenshot crop."""
from __future__ import annotations

from collections.abc import Iterator

from ..config import VisionModelSettings
from ..events import Target, TargetKind
from .prompts import SYSTEM, build_prompt


class OllamaVisionClient:
    def __init__(self, settings: VisionModelSettings) -> None:
        import ollama

        self._settings = settings
        self._client = ollama.Client(host=settings.host, timeout=settings.timeout_s)

    def stream(self, kind: TargetKind, target: Target) -> Iterator[str]:
        if not target.image_png:
            raise ValueError("vision client called without an image")
        stream = self._client.chat(
            model=self._settings.model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_prompt("image", target), "images": [target.image_png]},
            ],
            stream=True,
            keep_alive=self._settings.keep_alive,
            options={"num_predict": self._settings.max_tokens},
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content") if isinstance(chunk, dict) else chunk.message.content
            if content:
                yield content
