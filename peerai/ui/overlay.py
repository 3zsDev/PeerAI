"""Transparent, topmost, click-through window that draws the highlight rectangle."""
from __future__ import annotations

import sys
import tkinter as tk

from ..events import Rect

_KEY = "#010203"  # colour treated as fully transparent


class Overlay:
    def __init__(self, root: tk.Tk, screen: Rect, colour: str = "#3fd0ff") -> None:
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.geometry(f"{screen.width}x{screen.height}+{screen.left}+{screen.top}")
        self._win.configure(bg=_KEY)
        self._screen = screen
        self._colour = colour
        self._canvas = tk.Canvas(self._win, bg=_KEY, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._rect_id: int | None = None
        self._label_id: int | None = None
        self._current: Rect | None = None
        if sys.platform == "win32":
            self._win.attributes("-transparentcolor", _KEY)
            self._win.after(50, self._make_click_through)
        else:
            self._win.attributes("-alpha", 0.35)

    def _make_click_through(self) -> None:
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())  # type: ignore[attr-defined]
            GWL_EXSTYLE = -20
            WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW = 0x80000, 0x20, 0x80
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)  # type: ignore[attr-defined]
            ctypes.windll.user32.SetWindowLongW(  # type: ignore[attr-defined]
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    @property
    def rect(self) -> Rect:
        return self._screen

    def show(self, rect: Rect, label: str = "", armed: bool = False) -> None:
        self.clear()
        self._current = rect
        l, t = rect.left - self._screen.left, rect.top - self._screen.top
        r, b = rect.right - self._screen.left, rect.bottom - self._screen.top
        self._rect_id = self._canvas.create_rectangle(l, t, r, b, outline=self._colour, width=3 if armed else 2, dash=() if armed else (6, 4))
        if label:
            self._label_id = self._canvas.create_text(l + 4, max(0, t - 14), text=label, anchor="w", fill=self._colour, font=("Segoe UI", 9))

    def clear(self) -> None:
        if self._rect_id is not None:
            self._canvas.delete(self._rect_id)
            self._rect_id = None
        if self._label_id is not None:
            self._canvas.delete(self._label_id)
            self._label_id = None
        self._current = None
