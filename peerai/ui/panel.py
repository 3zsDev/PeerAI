"""Docked side panel showing the streamed model output."""
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext

from ..events import Rect

BG, FG, DIM, ACCENT = "#0b1420", "#d7e6f5", "#7f93a8", "#3fd0ff"


class Panel:
    def __init__(self, root: tk.Tk, screen: Rect, width: int = 380) -> None:
        self._win = tk.Toplevel(root)
        self._win.title("peerai")
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._rect = Rect(screen.right - width, screen.top, screen.right, screen.bottom)
        self._win.geometry(f"{width}x{screen.height}+{self._rect.left}+{self._rect.top}")
        self._win.configure(bg=BG)

        self._header = tk.Label(self._win, text="peerai", anchor="w", bg=BG, fg=ACCENT, font=("Segoe UI", 11, "bold"), padx=12, pady=8)
        self._header.pack(fill="x")
        self._sub = tk.Label(self._win, text="", anchor="w", bg=BG, fg=DIM, font=("Segoe UI", 9), padx=12)
        self._sub.pack(fill="x")
        self._body = scrolledtext.ScrolledText(self._win, wrap="word", bg=BG, fg=FG, insertbackground=FG, relief="flat", font=("Segoe UI", 11), padx=12, pady=8, state="disabled")
        self._body.pack(fill="both", expand=True)
        self._status = tk.Label(self._win, text="listening", anchor="w", bg=BG, fg=DIM, font=("Segoe UI", 9), padx=12, pady=6)
        self._status.pack(fill="x")

    @property
    def rect(self) -> Rect:
        return self._rect

    def set_header(self, app: str, kind: str, title: str = "") -> None:
        self._header.configure(text=f"{kind}  ·  {app or 'unknown app'}")
        self._sub.configure(text=title[:80])

    def set_body(self, text: str) -> None:
        self._body.configure(state="normal")
        self._body.delete("1.0", "end")
        self._body.insert("end", text)
        self._body.configure(state="disabled")
        self._body.see("end")

    def set_status(self, text: str, colour: str = DIM) -> None:
        self._status.configure(text=text, fg=colour)

    def clear(self) -> None:
        self._header.configure(text="peerai")
        self._sub.configure(text="")
        self.set_body("")
        self.set_status("listening")
