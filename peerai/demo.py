"""Headless run of the whole pipeline. Works without a display; prints to the console."""
from __future__ import annotations

import time

from .ai.router import Router
from .config import Settings
from .content.resolver import Blocked, Resolver
from .events import AiResult, Fixation, FixationEnd
from .fixation import FixationDetector, TargetHysteresis
from .input.base import PointerSource


def run_headless(settings: Settings, pointer: PointerSource, resolver: Resolver, router_factory, seconds: float = 6.0, radius_px: int | None = None) -> list[str]:
    log: list[str] = []
    last_text: dict[str, str] = {}

    def emit(result: AiResult) -> None:
        last_text[result.target_hash] = result.text
        if result.done:
            line = f"  -> [{result.kind}] {result.text.strip()}" if not result.error else f"  -> error: {result.error}"
            print(line)
            log.append(line)

    router: Router = router_factory(emit)
    detector = FixationDetector(dwell_s=settings.dwell_s, radius_px=radius_px or settings.radius_px, extend_every_s=settings.extend_every_ms / 1000)
    hyst = TargetHysteresis(margin_px=settings.rearm_margin_px, rearm_s=settings.rearm_ms / 1000)
    pointer.start()
    deadline = time.monotonic() + seconds
    interval = 1.0 / settings.poll_hz
    try:
        while time.monotonic() < deadline:
            sample = pointer.poll()
            if sample is None:
                if getattr(pointer, "exhausted", False):
                    break
                time.sleep(interval)
                continue
            hyst.observe(sample.x, sample.y, sample.t)
            event = detector.feed(sample)
            if isinstance(event, Fixation):
                try:
                    target = resolver.resolve(event.x, event.y)
                except Blocked as b:
                    line = f"fixation at ({event.x},{event.y}) refused: {b.reason}"
                    print(line)
                    log.append(line)
                    continue
                if target is None:
                    continue
                if hyst.accept(target.bbox, event.x, event.y, sample.t):
                    line = f"fixation at ({event.x},{event.y}) after {event.duration*1000:.0f} ms -> {target.control_type or target.kind_hint} in {target.app_name}"
                    print(line)
                    log.append(line)
                    router.submit(target)
            elif isinstance(event, FixationEnd):
                pass
            time.sleep(interval)
    finally:
        pointer.stop()
        router.join(timeout=5)
    return log
