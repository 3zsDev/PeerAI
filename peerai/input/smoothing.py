"""Filters for noisy gaze estimates."""
from __future__ import annotations

import math


class EmaFilter:
    """Exponential moving average on (x, y)."""

    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = alpha
        self._x: float | None = None
        self._y: float | None = None

    def reset(self) -> None:
        self._x = self._y = None

    def update(self, x: float, y: float) -> tuple[float, float]:
        if self._x is None or self._y is None:
            self._x, self._y = x, y
        else:
            self._x += self.alpha * (x - self._x)
            self._y += self.alpha * (y - self._y)
        return self._x, self._y


class OneEuroFilter:
    """One Euro filter: low lag on fast moves, strong smoothing when still.

    Casiez, Roussel, Vogel (CHI 2012).
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._prev: tuple[float, float] | None = None
        self._dprev = (0.0, 0.0)
        self._tprev: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self) -> None:
        self._prev = None
        self._tprev = None
        self._dprev = (0.0, 0.0)

    def update(self, x: float, y: float, t: float) -> tuple[float, float]:
        if self._prev is None or self._tprev is None:
            self._prev, self._tprev = (x, y), t
            return x, y
        dt = max(1e-3, t - self._tprev)
        self._tprev = t
        out = []
        new_d = []
        for value, prev, dprev in zip((x, y), self._prev, self._dprev):
            dx = (value - prev) / dt
            a_d = self._alpha(self.d_cutoff, dt)
            dx_hat = dprev + a_d * (dx - dprev)
            cutoff = self.min_cutoff + self.beta * abs(dx_hat)
            a = self._alpha(cutoff, dt)
            out.append(prev + a * (value - prev))
            new_d.append(dx_hat)
        self._prev = (out[0], out[1])
        self._dprev = (new_d[0], new_d[1])
        return self._prev
