"""Deterministic content for tests and --demo: a fixed set of labelled blocks."""
from __future__ import annotations

from ..events import Rect, Target


class FakeContentSource:
    def __init__(self, blocks: list[Target] | None = None) -> None:
        self.blocks = blocks or [
            Target(
                bbox=Rect(100, 200, 500, 420),
                text=(
                    "The mitochondrion is a double-membrane-bound organelle found in most "
                    "eukaryotic organisms. Mitochondria generate most of the cell's supply of "
                    "adenosine triphosphate, used as a source of chemical energy."
                ),
                kind_hint="text",
                app_name="chrome.exe",
                window_title="Mitochondrion - Wikipedia",
                control_type="Text",
            ),
            Target(
                bbox=Rect(800, 200, 1100, 420),
                text="What is the capital of Australia?",
                kind_hint="question",
                app_name="notepad.exe",
                window_title="quiz.txt - Notepad",
                control_type="Document",
            ),
            Target(
                bbox=Rect(400, 600, 800, 800),
                text="",
                kind_hint="image",
                app_name="explorer.exe",
                window_title="Pictures",
                control_type="Image",
                image_png=b"\x89PNG\r\n\x1a\nfake",
            ),
        ]

    def at(self, x: int, y: int) -> Target | None:
        for block in self.blocks:
            if block.bbox.contains(x, y):
                return block
        return None
