from peerai.events import Fixation, FixationEnd, PointerSample, Rect
from peerai.fixation import FixationDetector, TargetHysteresis


def feed_series(det, samples):
    return [det.feed(PointerSample(x, y, t)) for x, y, t in samples]


def test_fires_only_after_dwell():
    det = FixationDetector(dwell_s=0.7, radius_px=30)
    out = feed_series(det, [(100, 100, 0.0), (105, 102, 0.3), (103, 99, 0.69), (101, 100, 0.71)])
    assert out[:3] == [None, None, None]
    assert isinstance(out[3], Fixation)
    assert (out[3].x, out[3].y) == (100, 100)  # anchored at the first sample


def test_movement_resets_the_timer():
    det = FixationDetector(dwell_s=0.7, radius_px=30)
    out = feed_series(det, [(100, 100, 0.0), (200, 100, 0.5), (200, 100, 1.1), (200, 100, 1.25)])
    assert out[:3] == [None, None, None]
    assert isinstance(out[3], Fixation)


def test_extension_events_and_end():
    det = FixationDetector(dwell_s=0.7, radius_px=30, extend_every_s=0.5)
    out = feed_series(det, [(0, 0, 0.0), (0, 0, 0.7), (0, 0, 1.0), (0, 0, 1.2), (0, 0, 1.8), (500, 500, 2.0)])
    kinds = [type(o).__name__ if o else None for o in out]
    assert kinds == [None, "Fixation", None, "Fixation", "Fixation", "FixationEnd"]
    assert det.active is False


def test_hysteresis_switches_only_after_leaving():
    h = TargetHysteresis(margin_px=40, rearm_s=0.3)
    a, b = Rect(0, 0, 100, 100), Rect(500, 0, 600, 100)
    assert h.accept(a, 50, 50, 0.0) is True
    assert h.accept(a, 50, 50, 1.0) is False  # same target: nothing new
    # pointer arrives in b but has only just left a
    assert h.accept(b, 550, 50, 1.1) is False
    assert h.accept(b, 550, 50, 1.45) is True  # 0.35 s outside a
    assert h.current == b


def test_hysteresis_uses_observe_history():
    h = TargetHysteresis(margin_px=40, rearm_s=0.3)
    a, b = Rect(0, 0, 100, 100), Rect(500, 0, 600, 100)
    h.accept(a, 50, 50, 0.0)
    h.observe(550, 50, 1.0)  # pointer thread saw us leave at t=1.0
    assert h.accept(b, 550, 50, 1.35) is True
