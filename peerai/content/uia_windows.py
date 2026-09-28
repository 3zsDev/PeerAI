"""Windows UI Automation content source.

Finds the control under a point and walks up to the nearest block-level
control that has readable text or a reasonable size. All calls must happen on
one thread (COM apartment); the app runs the resolver on a dedicated thread.
"""
from __future__ import annotations

import os
import sys

from ..config import Settings
from ..events import Rect, Target, TargetKind

BLOCK_TYPES = {"Image", "Text", "Edit", "Document", "Hyperlink", "ListItem", "Group", "Pane", "DataItem", "TreeItem"}
STOP_TYPES = {"Window"}


class UiaContentSource:
    def __init__(self, settings: Settings) -> None:
        if sys.platform != "win32":
            raise RuntimeError("UiaContentSource only works on Windows")
        import uiautomation as auto  # type: ignore[import-not-found]

        self._auto = auto
        self._settings = settings
        self._own_pid = os.getpid()
        self._process_names: dict[int, str] = {}

    def at(self, x: int, y: int) -> Target | None:
        auto = self._auto
        try:
            control = auto.ControlFromPoint(x, y)
        except Exception:
            return None
        if control is None:
            return None

        pid = _safe(lambda: control.ProcessId, 0)
        if pid == self._own_pid:
            return None  # never scan our own panel or overlay

        block = self._walk_up_to_block(control)
        if block is None:
            return None

        rect = _safe(lambda: block.BoundingRectangle, None)
        if rect is None:
            return None
        bbox = Rect(int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        text = self._extract_text(block)[: self._settings.max_text_chars]
        control_type = _safe(lambda: block.ControlTypeName, "")
        top = _safe(lambda: block.GetTopLevelControl(), None)
        title = _safe(lambda: top.Name, "") if top is not None else ""
        return Target(
            bbox=bbox,
            text=text,
            kind_hint=_kind_hint(control_type, text),
            app_name=self._process_name(pid),
            window_title=title,
            control_type=control_type,
            process_id=pid,
        )

    def _walk_up_to_block(self, control):
        min_w, min_h = self._settings.min_block_size
        node = control
        for _ in range(12):
            if node is None:
                return None
            ctype = _safe(lambda: node.ControlTypeName, "")
            if ctype in STOP_TYPES:
                return node
            rect = _safe(lambda: node.BoundingRectangle, None)
            big_enough = rect is not None and (rect.right - rect.left) >= min_w and (rect.bottom - rect.top) >= min_h
            if ctype == "Image":
                return node
            if ctype in BLOCK_TYPES and (big_enough or self._extract_text(node)):
                return node
            if big_enough and self._extract_text(node):
                return node
            node = _safe(lambda: node.GetParentControl(), None)
        return control

    def _extract_text(self, control) -> str:
        name = _safe(lambda: control.Name, "") or ""
        if len(name.strip()) >= 20:
            return name.strip()
        value = _safe(lambda: control.GetValuePattern().Value, "") or ""
        if value.strip():
            return value.strip()
        doc = _safe(lambda: control.GetTextPattern().DocumentRange.GetText(-1), "") or ""
        if doc.strip():
            return doc.strip()
        return name.strip()

    def _process_name(self, pid: int) -> str:
        if pid in self._process_names:
            return self._process_names[pid]
        name = ""
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                    name = os.path.basename(buf.value)
                kernel32.CloseHandle(handle)
        except Exception:
            name = ""
        self._process_names[pid] = name
        return name


def _kind_hint(control_type: str, text: str) -> TargetKind:
    if control_type == "Image":
        return "image"
    if control_type in {"Button", "CheckBox", "RadioButton", "MenuItem", "TabItem", "ComboBox", "Slider"}:
        return "ui_element"
    if text:
        return "text"
    return "unknown"


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default
