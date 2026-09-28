"""Model clients stream text for a target. Ollama, DeepSeek, or anything OpenAI-compatible."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from ..events import Target, TargetKind


class AiClient(Protocol):
    def stream(self, kind: TargetKind, target: Target) -> Iterator[str]:
        """Yield text chunks. Raise on hard failure."""
        ...
