"""Mouse pointer as the gaze stand-in. Windows via ctypes; elsewhere via pynput."""
from __future__ import annotations

import ctypes
import sys
import time

from ..events import PointerSample


class MousePointerSource:
    def __init__(self) -> None:
        self._get = self._windows_getter() if sys.platform == "win32" else self._pynput_getter()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def poll(self) -> PointerSample | None:
        pos = self._get()
        if pos is None:
            return None
        return PointerSample(pos[0], pos[1], time.monotonic())

    @staticmethod
    def _windows_getter():
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        def get() -> tuple[int, int] | None:
            pt = POINT()
            if user32.GetCursorPos(ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
            return None

        return get

    @staticmethod
    def _pynput_getter():
        try:
            from pynput import mouse

            controller = mouse.Controller()
        except Exception:
            return lambda: None

        def get() -> tuple[int, int] | None:
            try:
                x, y = controller.position
                return int(x), int(y)
            except Exception:
                return None

        return get
