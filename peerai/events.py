"""Plain data types passed between pipeline stages."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class PointerSample:
    x: int
    y: int
    t: float  # monotonic seconds


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    def contains(self, x: int, y: int, margin: int = 0) -> bool:
        return (
            self.left - margin <= x < self.right + margin
            and self.top - margin <= y < self.bottom + margin
        )

    def center(self) -> tuple[int, int]:
        return (self.left + self.right) // 2, (self.top + self.bottom) // 2


@dataclass(frozen=True)
class Fixation:
    """Pointer has stayed inside a small radius for at least the dwell time."""

    x: int
    y: int
    started_at: float
    duration: float  # seconds held so far


@dataclass(frozen=True)
class FixationEnd:
    started_at: float
    ended_at: float


TargetKind = Literal["image", "text", "question", "code", "ui_element", "unknown"]


@dataclass
class Target:
    """What is under the gaze point, after snapping to a content block."""

    bbox: Rect
    text: str = ""
    kind_hint: TargetKind = "unknown"
    app_name: str = ""
    window_title: str = ""
    control_type: str = ""
    process_id: int = 0
    image_png: bytes | None = None
    hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        h = hashlib.sha1()
        h.update(self.app_name.encode("utf-8", "replace"))
        h.update(repr((self.bbox.left, self.bbox.top, self.bbox.right, self.bbox.bottom)).encode())
        h.update(self.text[:500].encode("utf-8", "replace"))
        if self.image_png:
            h.update(hashlib.sha1(self.image_png).digest())
        return h.hexdigest()


@dataclass
class AiResult:
    target_hash: str
    kind: TargetKind
    text: str
    done: bool = False
    error: str | None = None
