# peerai

Look at something on your screen, and a local model explains it in a side panel.
Inspired by the Iron Man HUD. Windows first; the mouse pointer stands in for
your gaze until you calibrate the webcam.

## How it works

```
pointer (mouse | webcam gaze) --> fixation gate (700 ms dwell) --> what's under it? (UI Automation, screenshot fallback)
                                                                        |
        side panel + highlight  <--  router (classify, cache, one job at a time)  <--  model (Ollama / OpenAI-compatible)
```

Three rules keep it from being annoying:

1. **Nothing fires until you've held still for `dwell_ms`** (default 700, use 600 to 800). In
   `confirm` mode (default) the dwell only draws the highlight; **F8** runs the scan. In `auto`
   mode the dwell runs the scan. **Esc** clears.
2. **It never scans its own output.** Fixations inside the panel are dropped, and any control
   that belongs to peerai's own process is ignored.
3. **Gaze is a coarse pointer that snaps to a content block**, never a precise cursor. A new block
   only takes over after the pointer has clearly left the old one (hysteresis).

## Install (Windows, Python 3.11 or 3.12)

```powershell
git clone <this repo> ; cd peerai
py -3.12 -m venv .venv ; .venv\Scripts\activate
pip install -e .            # add ".[webcam]" for the webcam gaze source
```

Models (Ollama must be installed and running):

```powershell
ollama pull qwen2.5:3b      # text: summaries and answers
ollama pull qwen2.5vl:3b    # vision: images and regions with no readable text
ollama list                 # confirm both are there
```

On a laptop without a discrete GPU, expect a few seconds per text answer and ten seconds or more
per image. If that is too slow, `config.toml` lets you point the text model at any
OpenAI-compatible endpoint:

| Backend | `base_url` | `model` | Notes |
|---|---|---|---|
| Ollama (default) | `http://localhost:11434/v1` | `qwen2.5:3b` | Fully local |
| Official DeepSeek API | `https://api.deepseek.com/v1` | `deepseek-chat` | Sanctioned and cheap; needs an API key |
| deepseek-bridge | `http://127.0.0.1:11435/v1` | `deepseek-chat` | Unofficial scraper of the DeepSeek web UI. Can break or get your account rate-limited at any time. Not recommended for this app's request pattern. |

Images always go to the Ollama vision model. DeepSeek has no vision model.

## Run

```powershell
peerai                        # mouse pointer, UI Automation, Ollama, confirm mode
peerai --trigger auto         # scan on dwell without pressing F8
peerai calibrate              # 9-point webcam calibration (needs .[webcam])
peerai --input webcam         # use the calibrated webcam gaze
peerai --demo --input fake --content fake --ai fake   # headless pipeline check, any OS
```

Configuration is read from `config.toml` in the current directory, then `~/.peerai/config.toml`.

## Verifying each phase on the laptop

1. **Pipeline:** `peerai --demo --input fake --content fake --ai fake` prints three fixations and
   three fake answers. `python -m pytest` passes.
2. **Windows content and UI:** run `peerai --ai fake`. Hover a paragraph in Notepad, a paragraph
   in Chrome, and a file icon in Explorer. The dashed rectangle should land on the block and the
   status line should read "press F8 to scan". Open a window whose title contains "bank"; the
   status line should say it was not scanned.
3. **Text model:** run `peerai`. Hover a paragraph, press F8: a summary should stream within a
   few seconds and the rectangle turns solid. Hover a question, press F8: you get an answer.
   Move away: the panel keeps its text until the next scan or Esc. Re-scan the same block: it
   comes back from cache instantly.
4. **Vision:** hover an image in an Explorer preview or a browser, press F8: a description streams.
5. **Webcam:** `peerai calibrate`, then `peerai --input webcam`. The highlight should follow your
   gaze between large blocks. Head movement after calibration degrades accuracy; recalibrate.

## Privacy

Camera frames never leave the machine; only landmark features are used. Screen text and crops
are sent to whichever model endpoint `config.toml` names. With the Ollama defaults that is
localhost. Add words to `blocked_title_words` for anything you never want scanned.

## Layout

```
peerai/
  config.py           settings + config.toml loader
  events.py           PointerSample, Fixation, Target, AiResult
  fixation.py         dwell gate and target hysteresis
  input/              mouse, fake, webcam_gaze, calibration, smoothing
  content/            uia_windows, screenshot, resolver, fake
  ai/                 openai_compat (text), ollama_vision (images), router, prompts, fake
  ui/                 overlay, panel, app (thread wiring)
  privacy.py          window/process blocklist
  demo.py             headless runner
  main.py             CLI
```
