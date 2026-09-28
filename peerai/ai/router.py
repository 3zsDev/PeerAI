"""Classify a target, pick a client, run one job at a time, cache by target hash."""
from __future__ import annotations

import re
import threading
from collections import OrderedDict
from collections.abc import Callable

from ..events import AiResult, Target, TargetKind
from .base import AiClient

_CODE_HINTS = re.compile(
    r"(\bdef\b|\bclass\b|\bimport\b|\breturn\b|\bfunction\b|\bconst\b|\blet\b|\bvar\b|=>|\{|\}|;\s*$|#include|\bpublic\b|\bstatic\b)",
    re.MULTILINE,
)
_QUESTION_HINTS = re.compile(r"\?\s*$|^\s*(q\d*[.:)]|question\s*\d*[.:)])|^\s*(what|which|why|how|when|where|who)\b", re.IGNORECASE | re.MULTILINE)


def classify(target: Target) -> TargetKind:
    text = target.text.strip()
    if target.image_png and len(text) < 40:
        return "image"
    if target.kind_hint == "ui_element":
        return "ui_element"
    if target.kind_hint == "image" and target.image_png:
        return "image"
    if not text:
        return "image" if target.image_png else "unknown"
    lines = [ln for ln in text.splitlines() if ln.strip()]
    code_hits = len(_CODE_HINTS.findall(text))
    if lines and code_hits >= max(3, len(lines) // 2) and len(text) > 40:
        return "code"
    if _QUESTION_HINTS.search(text) and len(text) < 600:
        return "question"
    return "text"


class Router:
    """Runs at most one model job at a time. A newer target cancels the older job."""

    def __init__(
        self,
        text_client: AiClient,
        vision_client: AiClient | None,
        emit: Callable[[AiResult], None],
        cache_size: int = 64,
    ) -> None:
        self._text = text_client
        self._vision = vision_client
        self._emit = emit
        self._cache: OrderedDict[str, AiResult] = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()
        self._current_hash: str | None = None
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None

    def cached(self, target_hash: str) -> AiResult | None:
        with self._lock:
            result = self._cache.get(target_hash)
            if result is not None:
                self._cache.move_to_end(target_hash)
            return result

    def submit(self, target: Target) -> TargetKind:
        kind = classify(target)
        cached = self.cached(target.hash)
        if cached is not None:
            self._emit(cached)
            return kind
        with self._lock:
            if self._current_hash == target.hash and self._thread and self._thread.is_alive():
                return kind
            self._cancel.set()
            self._cancel = threading.Event()
            cancel = self._cancel
            self._current_hash = target.hash
            self._thread = threading.Thread(target=self._run, args=(kind, target, cancel), daemon=True, name="peerai-ai")
            self._thread.start()
        return kind

    def cancel(self) -> None:
        with self._lock:
            self._cancel.set()
            self._current_hash = None

    def _run(self, kind: TargetKind, target: Target, cancel: threading.Event) -> None:
        client = self._text
        if kind == "image":
            if self._vision is None:
                self._emit(AiResult(target.hash, kind, "", done=True, error="no vision model configured"))
                return
            client = self._vision
        buf: list[str] = []
        try:
            for chunk in client.stream(kind, target):
                if cancel.is_set():
                    return
                buf.append(chunk)
                self._emit(AiResult(target.hash, kind, "".join(buf), done=False))
        except Exception as exc:  # model down, network, bad response
            if cancel.is_set():
                return
            self._emit(AiResult(target.hash, kind, "".join(buf), done=True, error=f"{type(exc).__name__}: {exc}"))
            return
        if cancel.is_set():
            return
        result = AiResult(target.hash, kind, "".join(buf).strip(), done=True)
        with self._lock:
            self._cache[target.hash] = result
            self._cache.move_to_end(target.hash)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        self._emit(result)

    def join(self, timeout: float | None = None) -> None:
        t = self._thread
        if t is not None:
            t.join(timeout)
