"""Settings loaded from config.toml with sane defaults."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

TriggerMode = Literal["auto", "confirm"]


@dataclass
class TextModelSettings:
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen2.5:3b"
    api_key: str = "ollama"
    max_tokens_summary: int = 400
    max_tokens_answer: int = 800
    timeout_s: float = 60.0


@dataclass
class VisionModelSettings:
    host: str = "http://localhost:11434"
    model: str = "qwen2.5vl:3b"
    keep_alive: str = "10m"
    max_tokens: int = 300
    timeout_s: float = 120.0


@dataclass
class Settings:
    dwell_ms: int = 700
    radius_px: int = 30
    poll_hz: int = 60
    rearm_margin_px: int = 40
    rearm_ms: int = 300
    extend_every_ms: int = 500
    trigger_mode: TriggerMode = "confirm"
    confirm_key: str = "f8"
    clear_key: str = "esc"
    panel_width: int = 380
    max_text_chars: int = 4000
    screenshot_box: tuple[int, int] = (600, 400)
    min_block_size: tuple[int, int] = (120, 40)
    blocked_title_words: list[str] = field(
        default_factory=lambda: ["bank", "password", "1password", "bitwarden", "keepass", "lastpass"]
    )
    blocked_processes: list[str] = field(default_factory=list)
    text: TextModelSettings = field(default_factory=TextModelSettings)
    vision: VisionModelSettings = field(default_factory=VisionModelSettings)
    webcam_index: int = 0
    webcam_radius_px: int = 80
    calibration_path: Path = field(default_factory=lambda: Path.home() / ".peerai" / "calibration.json")

    @property
    def dwell_s(self) -> float:
        return self.dwell_ms / 1000.0


def _apply(obj: Any, data: dict[str, Any]) -> None:
    for key, value in data.items():
        if not hasattr(obj, key):
            continue
        current = getattr(obj, key)
        if isinstance(value, dict) and hasattr(current, "__dataclass_fields__"):
            _apply(current, value)
        elif isinstance(current, Path):
            setattr(obj, key, Path(value).expanduser())
        elif isinstance(current, tuple) and isinstance(value, list):
            setattr(obj, key, tuple(value))
        else:
            setattr(obj, key, value)


def load_settings(path: str | Path | None = None) -> Settings:
    settings = Settings()
    candidates = [Path(path)] if path else [Path("config.toml"), Path.home() / ".peerai" / "config.toml"]
    for candidate in candidates:
        if candidate.is_file():
            with candidate.open("rb") as fh:
                data = tomllib.load(fh)
            ai = data.pop("ai", {})
            _apply(settings, data)
            if "text" in ai:
                _apply(settings.text, ai["text"])
            if "vision" in ai:
                _apply(settings.vision, ai["vision"])
            break
    settings.dwell_ms = max(100, int(settings.dwell_ms))
    return settings
