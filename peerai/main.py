"""Command line entry point."""
from __future__ import annotations

import argparse
import sys

from .config import Settings, load_settings


def _build_ai(settings: Settings, ai: str):
    from .ai.router import Router

    if ai == "fake":
        from .ai.fake import FakeAiClient

        text = vision = FakeAiClient()
    else:
        from .ai.ollama_vision import OllamaVisionClient
        from .ai.openai_compat import OpenAICompatClient

        text = OpenAICompatClient(settings.text)
        vision = OllamaVisionClient(settings.vision)
    return lambda emit: Router(text, vision, emit)


def _build_pointer(settings: Settings, name: str):
    if name == "fake":
        from .input.fake import FakePointerSource

        return FakePointerSource()
    if name == "webcam":
        from .input.webcam_gaze import WebcamGazeSource

        return WebcamGazeSource(settings)
    from .input.mouse import MousePointerSource

    return MousePointerSource()


def _build_content(settings: Settings, name: str):
    if name == "fake":
        from .content.fake import FakeContentSource

        return FakeContentSource()
    from .content.uia_windows import UiaContentSource

    return UiaContentSource(settings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="peerai", description="Look at something; get an explanation in a side panel.")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "calibrate"])
    parser.add_argument("--config", default=None, help="path to config.toml")
    parser.add_argument("--input", default="mouse", choices=["mouse", "webcam", "fake"])
    parser.add_argument("--content", default="uia" if sys.platform == "win32" else "fake", choices=["uia", "fake"])
    parser.add_argument("--ai", default="ollama", choices=["ollama", "fake"])
    parser.add_argument("--demo", action="store_true", help="headless: print to console instead of drawing windows")
    parser.add_argument("--seconds", type=float, default=6.0, help="how long a --demo run lasts")
    parser.add_argument("--trigger", default=None, choices=["auto", "confirm"], help="override trigger mode")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    if args.trigger:
        settings.trigger_mode = args.trigger

    if args.command == "calibrate":
        from .input.calibration import run_calibration

        return run_calibration(settings)

    pointer = _build_pointer(settings, args.input)
    content = _build_content(settings, args.content)
    router_factory = _build_ai(settings, args.ai)
    radius = settings.webcam_radius_px if args.input == "webcam" else None

    from .content.resolver import Resolver

    if args.demo:
        from .demo import run_headless

        resolver = Resolver(content, settings)
        run_headless(settings, pointer, resolver, router_factory, seconds=args.seconds, radius_px=radius)
        return 0

    from .content.screenshot import crop_png, primary_screen
    from .ui.app import App, set_dpi_aware

    set_dpi_aware()
    screen = primary_screen()
    holder: dict[str, App] = {}
    resolver = Resolver(content, settings, excluded_rects=lambda: holder["app"].excluded_rects() if "app" in holder else [], crop=crop_png, screen=lambda: screen)
    app = App(settings, pointer, resolver, router_factory(lambda r: holder["app"]._on_ai_result(r)), screen, radius_px=radius)
    holder["app"] = app
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
