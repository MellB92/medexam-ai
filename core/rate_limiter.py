"""Simple rate limiter utilities for API throttling."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: float
    burst: float

    @classmethod
    def from_rpm(cls, rpm: float, burst: float | None = None) -> "RateLimitConfig":
        burst_capacity = burst if burst is not None else max(1.0, rpm)
        return cls(requests_per_minute=max(0.01, rpm), burst=max(1.0, burst_capacity))


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._tokens = config.burst
        self._last_refill = time.time()

    def allow(self) -> Tuple[bool, float]:
        with self._lock:
            now = time.time()
            refill_rate = self.config.requests_per_minute / 60.0
            elapsed = max(0.0, now - self._last_refill)
            self._tokens = min(
                self.config.burst,
                self._tokens + elapsed * refill_rate,
            )
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True, 0.0

            needed = 1.0 - self._tokens
            wait_seconds = needed / max(refill_rate, 1e-6)
            return False, wait_seconds

    def update(self, config: RateLimitConfig) -> None:
        with self._lock:
            self.config = config
            self._tokens = min(self._tokens, config.burst)
            self._last_refill = time.time()
