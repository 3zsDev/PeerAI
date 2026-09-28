"""9-point calibration: map iris features to screen coordinates with ridge regression."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from ..config import Settings

POINTS = [(0.1, 0.1), (0.5, 0.1), (0.9, 0.1), (0.1, 0.5), (0.5, 0.5), (0.9, 0.5), (0.1, 0.9), (0.5, 0.9), (0.9, 0.9)]


def expand(features: np.ndarray) -> np.ndarray:
    """Degree-2 polynomial expansion with bias. features: (n, d)."""
    f = np.atleast_2d(features)
    n, d = f.shape
    cols = [np.ones((n, 1)), f]
    for i in range(d):
        for j in range(i, d):
            cols.append((f[:, i] * f[:, j])[:, None])
    return np.hstack(cols)


class GazeModel:
    def __init__(self, weights: np.ndarray | None = None) -> None:
        self.weights = weights  # (k, 2)

    @classmethod
    def fit(cls, features: np.ndarray, targets: np.ndarray, ridge: float = 1e-2) -> "GazeModel":
        X = expand(features)
        A = X.T @ X + ridge * np.eye(X.shape[1])
        W = np.linalg.solve(A, X.T @ targets)
        return cls(W)

    def predict(self, features: np.ndarray) -> tuple[float, float]:
        assert self.weights is not None
        out = expand(features) @ self.weights
        return float(out[0, 0]), float(out[0, 1])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"weights": self.weights.tolist()}))

    @classmethod
    def load(cls, path: Path) -> "GazeModel":
        data = json.loads(path.read_text())
        return cls(np.array(data["weights"], dtype=float))


def run_calibration(settings: Settings) -> int:
    """Fullscreen dots; look at each one; fit and save the model."""
    import tkinter as tk

    from .webcam_gaze import IrisFeatureExtractor

    extractor = IrisFeatureExtractor(settings.webcam_index)
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")
    W, H = root.winfo_screenwidth(), root.winfo_screenheight()
    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    msg = canvas.create_text(W // 2, H // 2 - 60, text="Keep your head still. Look at each dot until it turns green. Esc to abort.", fill="white", font=("Segoe UI", 16))
    root.bind("<Escape>", lambda e: root.destroy())
    root.update()
    time.sleep(2)
    canvas.delete(msg)

    feats: list[np.ndarray] = []
    targs: list[tuple[float, float]] = []
    for px, py in POINTS:
        x, y = int(px * W), int(py * H)
        dot = canvas.create_oval(x - 12, y - 12, x + 12, y + 12, fill="#ff4040", outline="")
        root.update()
        time.sleep(0.8)  # let the eyes settle
        collected = 0
        t_end = time.monotonic() + 1.5
        while time.monotonic() < t_end:
            f = extractor.read()
            root.update()
            if f is not None:
                feats.append(f)
                targs.append((x, y))
                collected += 1
        canvas.itemconfigure(dot, fill="#40ff40" if collected >= 10 else "#ffa040")
        root.update()
        time.sleep(0.3)
        canvas.delete(dot)
    root.destroy()
    extractor.close()

    if len(feats) < 40:
        print(f"calibration failed: only {len(feats)} usable frames (face not found?)")
        return 1
    model = GazeModel.fit(np.array(feats), np.array(targs, dtype=float))
    model.save(settings.calibration_path)
    pred = np.array([model.predict(f) for f in feats])
    err = np.linalg.norm(pred - np.array(targs), axis=1)
    print(f"saved {settings.calibration_path}; mean error {err.mean():.0f} px on the calibration frames (real use will be worse)")
    return 0
