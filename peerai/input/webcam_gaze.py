"""Webcam gaze via MediaPipe FaceMesh iris landmarks.

Feature vector per frame (both eyes): iris centre position normalised inside
the eye box, plus nose position and inter-ocular distance as a head-pose
proxy. A calibrated ridge-regression model maps features to screen pixels.
Accuracy is block-level (roughly 100-200 px); the pipeline snaps to blocks
so that is enough.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from ..config import Settings
from ..events import PointerSample
from .smoothing import OneEuroFilter

# FaceMesh landmark indices (refine_landmarks=True adds iris points 468-477)
L_IRIS, R_IRIS = 468, 473
L_OUTER, L_INNER, L_TOP, L_BOTTOM = 33, 133, 159, 145
R_INNER, R_OUTER, R_TOP, R_BOTTOM = 362, 263, 386, 374
NOSE = 1


class IrisFeatureExtractor:
    def __init__(self, camera_index: int = 0) -> None:
        import cv2
        import mediapipe as mp

        self._cv2 = cv2
        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open webcam {camera_index}")
        self._mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        if not ok:
            return None
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        res = self._mesh.process(rgb)
        if not res.multi_face_landmarks:
            return None
        lm = res.multi_face_landmarks[0].landmark
        return features_from_landmarks([(p.x, p.y) for p in lm])

    def close(self) -> None:
        self._cap.release()
        self._mesh.close()


def features_from_landmarks(pts: list[tuple[float, float]]) -> np.ndarray:
    def eye(iris, outer, inner, top, bottom):
        ix, iy = pts[iris]
        ox, oy = pts[outer]
        nx, ny = pts[inner]
        ty, by = pts[top][1], pts[bottom][1]
        w = (nx - ox) or 1e-6
        h = (by - ty) or 1e-6
        return [(ix - ox) / w, (iy - ty) / h]

    left = eye(L_IRIS, L_OUTER, L_INNER, L_TOP, L_BOTTOM)
    right = eye(R_IRIS, R_INNER, R_OUTER, R_TOP, R_BOTTOM)
    nose = list(pts[NOSE])
    inter = float(np.hypot(pts[R_OUTER][0] - pts[L_OUTER][0], pts[R_OUTER][1] - pts[L_OUTER][1]))
    return np.array(left + right + nose + [inter], dtype=float)


class WebcamGazeSource:
    """PointerSource backed by the webcam. Runs capture on its own thread."""

    def __init__(self, settings: Settings) -> None:
        from .calibration import GazeModel

        if not settings.calibration_path.is_file():
            raise RuntimeError(f"no calibration at {settings.calibration_path}; run `peerai calibrate` first")
        self._model = GazeModel.load(settings.calibration_path)
        self._settings = settings
        self._filter = OneEuroFilter(min_cutoff=0.8, beta=0.01)
        self._latest: PointerSample | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="peerai-webcam")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def poll(self) -> PointerSample | None:
        with self._lock:
            return self._latest

    def _loop(self) -> None:
        extractor = IrisFeatureExtractor(self._settings.webcam_index)
        try:
            while not self._stop.is_set():
                f = extractor.read()
                if f is None:
                    continue
                x, y = self._model.predict(f)
                t = time.monotonic()
                sx, sy = self._filter.update(x, y, t)
                with self._lock:
                    self._latest = PointerSample(int(sx), int(sy), t)
        finally:
            extractor.close()
