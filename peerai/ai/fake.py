"""Canned model for tests and --demo."""
from __future__ import annotations

import time
from collections.abc import Iterator

from ..events import Target, TargetKind


class FakeAiClient:
    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s
        self.calls: list[tuple[TargetKind, str]] = []

    def stream(self, kind: TargetKind, target: Target) -> Iterator[str]:
        self.calls.append((kind, target.hash))
        words = f"[{kind}] fake answer for '{target.text[:40] or 'image'}' in {target.app_name}".split(" ")
        for w in words:
            if self.delay_s:
                time.sleep(self.delay_s)
            yield w + " "
