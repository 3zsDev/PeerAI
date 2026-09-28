"""Screenshot crops used when accessibility gives us nothing useful."""
from __future__ import annotations

import io

from ..events import Rect


def crop_png(rect: Rect) -> bytes:
    import mss
    from PIL import Image

    with mss.mss() as sct:
        shot = sct.grab({"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def box_around(x: int, y: int, size: tuple[int, int], screen: Rect) -> Rect:
    w, h = size
    left = max(screen.left, min(x - w // 2, screen.right - w))
    top = max(screen.top, min(y - h // 2, screen.bottom - h))
    return Rect(left, top, min(left + w, screen.right), min(top + h, screen.bottom))


def primary_screen() -> Rect:
    import mss

    with mss.mss() as sct:
        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
    return Rect(mon["left"], mon["top"], mon["left"] + mon["width"], mon["top"] + mon["height"])
