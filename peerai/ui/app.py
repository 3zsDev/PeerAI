"""Wires the pipeline: pointer thread -> fixation gate -> resolver -> router -> UI.

Threads:
  * pointer thread: polls the PointerSource, runs FixationDetector, posts events
  * resolver thread: runs content lookups (UIA needs its own COM apartment)
  * router worker: streams from the model (owned by Router)
  * main thread: tkinter, drains a queue and updates the overlay/panel
"""
from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Any

from ..ai.router import Router
from ..config import Settings
from ..content.resolver import Blocked, Resolver
from ..events import AiResult, Fixation, FixationEnd, PointerSample, Rect, Target
from ..fixation import FixationDetector, TargetHysteresis
from ..input.base import PointerSource
from .overlay import Overlay
from .panel import Panel


@dataclass
class _Resolved:
    target: Target | None
    fixation: Fixation
    blocked: str | None = None


class App:
    def __init__(self, settings: Settings, pointer: PointerSource, resolver: Resolver, router: Router, screen: Rect, radius_px: int | None = None) -> None:
        self._settings = settings
        self._pointer = pointer
        self._resolver = resolver
        self._router = router
        self._screen = screen
        self._ui_queue: queue.Queue[Any] = queue.Queue()
        self._resolve_queue: queue.Queue[Fixation | None] = queue.Queue(maxsize=2)
        self._stop = threading.Event()
        self._detector = FixationDetector(dwell_s=settings.dwell_s, radius_px=radius_px or settings.radius_px, extend_every_s=settings.extend_every_ms / 1000)
        self._hysteresis = TargetHysteresis(margin_px=settings.rearm_margin_px, rearm_s=settings.rearm_ms / 1000)
        self._active: Target | None = None
        self._armed = False

        self._root = tk.Tk()
        self._root.withdraw()
        self._overlay = Overlay(self._root, screen)
        self._panel = Panel(self._root, screen, width=settings.panel_width)

    def excluded_rects(self) -> list[Rect]:
        return [self._panel.rect]

    # ---- threads -------------------------------------------------------
    def _pointer_loop(self) -> None:
        interval = 1.0 / max(10, self._settings.poll_hz)
        self._pointer.start()
        try:
            while not self._stop.is_set():
                sample = self._pointer.poll()
                if sample is not None:
                    self._hysteresis.observe(sample.x, sample.y, sample.t)
                    event = self._detector.feed(sample)
                    if event is not None:
                        self._ui_queue.put(event)
                        if isinstance(event, Fixation):
                            try:
                                self._resolve_queue.put_nowait(event)
                            except queue.Full:
                                pass
                time.sleep(interval)
        finally:
            self._pointer.stop()

    def _resolver_loop(self) -> None:
        while not self._stop.is_set():
            try:
                fix = self._resolve_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if fix is None:
                continue
            try:
                target = self._resolver.resolve(fix.x, fix.y)
                self._ui_queue.put(_Resolved(target, fix))
            except Blocked as b:
                self._ui_queue.put(_Resolved(None, fix, blocked=b.reason))
            except Exception as exc:
                self._ui_queue.put(_Resolved(None, fix, blocked=f"lookup failed: {exc}"))

    def _on_ai_result(self, result: AiResult) -> None:
        self._ui_queue.put(result)

    # ---- main thread ---------------------------------------------------
    def _drain(self) -> None:
        try:
            while True:
                item = self._ui_queue.get_nowait()
                self._handle(item)
        except queue.Empty:
            pass
        if not self._stop.is_set():
            self._root.after(30, self._drain)

    def _handle(self, item: Any) -> None:
        if isinstance(item, FixationEnd):
            return  # keep the panel until the next target or Esc
        if isinstance(item, Fixation):
            return  # resolver will follow up
        if isinstance(item, _Resolved):
            if item.blocked:
                self._panel.set_status(f"not scanned: {item.blocked}", "#f0a050")
                return
            if item.target is None:
                return
            fix = item.fixation
            if not self._hysteresis.accept(item.target.bbox, fix.x, fix.y, fix.started_at + fix.duration):
                return
            self._active = item.target
            self._armed = False
            label = f"{item.target.control_type or item.target.kind_hint}"
            if self._settings.trigger_mode == "auto":
                self._fire()
            else:
                self._overlay.show(item.target.bbox, label, armed=False)
                self._panel.set_status(f"press {self._settings.confirm_key.upper()} to scan", "#3fd0ff")
            return
        if isinstance(item, AiResult):
            if self._active is None or item.target_hash != self._active.hash:
                return
            self._panel.set_body(item.text)
            if item.error:
                self._panel.set_status(f"error: {item.error}", "#f06060")
            elif item.done:
                self._panel.set_status("done")
            else:
                self._panel.set_status("thinking…")

    def _fire(self) -> None:
        if self._active is None:
            return
        self._armed = True
        kind = self._router.submit(self._active)
        self._overlay.show(self._active.bbox, kind, armed=True)
        self._panel.set_header(self._active.app_name, kind, self._active.window_title)
        if self._router.cached(self._active.hash) is None:
            self._panel.set_body("")
            self._panel.set_status("thinking…")

    def _clear(self) -> None:
        self._router.cancel()
        self._active = None
        self._armed = False
        self._hysteresis.clear()
        self._overlay.clear()
        self._panel.clear()

    def _bind_hotkeys(self) -> None:
        try:
            from pynput import keyboard
        except Exception:
            return
        confirm = self._settings.confirm_key.lower()
        clear = self._settings.clear_key.lower()

        def on_press(key) -> None:
            name = getattr(key, "name", None) or getattr(key, "char", None) or ""
            name = str(name).lower()
            if name == confirm:
                self._root.after(0, self._fire)
            elif name == clear:
                self._root.after(0, self._clear)

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def run(self) -> None:
        threading.Thread(target=self._pointer_loop, daemon=True, name="peerai-pointer").start()
        threading.Thread(target=self._resolver_loop, daemon=True, name="peerai-resolver").start()
        self._bind_hotkeys()
        self._root.after(30, self._drain)
        try:
            self._root.mainloop()
        finally:
            self._stop.set()


def set_dpi_aware() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
        except Exception:
            pass
