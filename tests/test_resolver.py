import os

import pytest

from peerai.config import Settings
from peerai.content.fake import FakeContentSource
from peerai.content.resolver import Blocked, Resolver
from peerai.events import Rect, Target


def test_excluded_rects_are_never_scanned():
    src = FakeContentSource()
    r = Resolver(src, Settings(), excluded_rects=lambda: [Rect(0, 0, 2000, 2000)])
    assert r.resolve(200, 300) is None


def test_own_process_is_never_scanned():
    src = FakeContentSource([Target(bbox=Rect(0, 0, 100, 100), text="our own panel text here", process_id=os.getpid())])
    assert Resolver(src, Settings()).resolve(10, 10) is None


def test_blocklist_refuses():
    src = FakeContentSource([Target(bbox=Rect(0, 0, 100, 100), text="balance: 12", window_title="My Bank - Chrome")])
    with pytest.raises(Blocked):
        Resolver(src, Settings()).resolve(10, 10)


def test_image_fallback_crops_when_text_is_thin():
    src = FakeContentSource([Target(bbox=Rect(0, 0, 300, 200), text="ok", control_type="Pane")])
    crops = []

    def crop(rect):
        crops.append(rect)
        return b"png-bytes"

    t = Resolver(src, Settings(), crop=crop, screen=lambda: Rect(0, 0, 1920, 1080)).resolve(10, 10)
    assert t is not None and t.image_png == b"png-bytes"
    assert crops == [Rect(0, 0, 300, 200)]


def test_tiny_control_uses_box_around_point():
    src = FakeContentSource([Target(bbox=Rect(100, 100, 110, 110), text="", control_type="Image", kind_hint="image")])
    t = Resolver(src, Settings(), crop=lambda r: b"x", screen=lambda: Rect(0, 0, 1920, 1080)).resolve(105, 105)
    assert t is not None and t.bbox == Rect(0, 0, 600, 400)


def test_text_target_not_cropped():
    src = FakeContentSource()
    t = Resolver(src, Settings(), crop=lambda r: b"x").resolve(200, 300)
    assert t is not None and t.image_png is None and t.kind_hint == "text"
