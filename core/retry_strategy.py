"""
Retry-Strategie mit exponentiellem Backoff und Fehlerklassifizierung (MED-003).

Diese Komponente ist provider-agnostisch und kann überall dort genutzt werden,
wo API-Aufrufe robust wiederholt werden sollen.
"""

from __future__ import annotations

import random
import time
import logging
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Tuple, Type, Any, Dict

logger = logging.getLogger(__name__)


# --- Fehlerklassen ---------------------------------------------------------

class RetryableError(Exception):
    """Basisfehler für retrybare Fehler."""


class RateLimitError(RetryableError):
    """429 oder provider-spezifische Quota-/RPM-Fehler."""


class NetworkError(RetryableError):
    """Netzwerk-/Timeout-/Verbindungsfehler."""


class ParseError(Exception):
    """Antwort konnte nicht geparst werden (gewöhnlich nicht retrybar)."""


# --- Konfiguration ---------------------------------------------------------

@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 8.0
    jitter: float = 0.0  # 0 = kein Jitter; ansonsten Zufallswert in [0, jitter]
    retry_on: Tuple[Type[BaseException], ...] = (RateLimitError, NetworkError)


class RetryStrategy:
    """Allgemeine Retry-Strategie mit exponentiellem Backoff.

    Usage:
        rs = RetryStrategy(RetryConfig(max_retries=2, backoff_factor=0.2))
        result = rs.run(callable_fn, *args, **kwargs)
    """

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config or RetryConfig()
        self.sleep_fn = sleep_fn

        # Test-/Diagnosehilfe
        self.attempt_count: int = 0
        self.delays: list[float] = []

    # ---------------------------- Ausführung -----------------------------
    def run(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Führt `fn` mit Retries aus und gibt das Ergebnis zurück.

        Raises:
            Exception: Letzter Fehler nach Ausschöpfen aller Wiederholungen.
        """
        last_err: Optional[BaseException] = None
        self.attempt_count = 0
        self.delays = []

        total_attempts = self.config.max_retries + 1  # inkl. Erstversuch

        for attempt in range(1, total_attempts + 1):
            self.attempt_count = attempt
            try:
                return fn(*args, **kwargs)
            except BaseException as e:  # noqa: BLE001 - wir klassifizieren selbst
                classified = self.classify_error(e)
                is_retryable = isinstance(classified, self.config.retry_on)
                last_err = classified

                # Letzter Versuch -> brich ab
                if attempt >= total_attempts or not is_retryable:
                    logger.error(
                        f"❌ Retry exhausted or non-retryable error: {type(classified).__name__}: {classified}"
                    )
                    raise classified

                # Backoff berechnen und schlafen
                delay = self._compute_delay(attempt)
                self.delays.append(delay)
                logger.warning(
                    f"⚠️ Retryable error ({type(classified).__name__}): {classified}. "
                    f"Retry {attempt}/{self.config.max_retries} in {delay:.2f}s"
                )
                self.sleep_fn(delay)

        # sollte nicht erreicht werden
        assert last_err is not None
        raise last_err

    # ---------------------------- Hilfsfunktionen ------------------------
    def _compute_delay(self, attempt: int) -> float:
        base = self.config.backoff_factor * (2 ** (attempt - 1))
        delay = min(base, self.config.max_backoff)
        if self.config.jitter and self.config.jitter > 0:
            delay += random.uniform(0, self.config.jitter)
        return delay

    # ---------------------------- Klassifizierung ------------------------
    @staticmethod
    def classify_error(err: BaseException) -> BaseException:
        """Klassifiziert den Fehler in RateLimitError, NetworkError, ParseError etc.

        Regeln (best-effort, provider-agnostisch):
        - HTTP 429 / "rate limit" im Text -> RateLimitError
        - requests.ConnectionError/Timeout oder SocketError -> NetworkError
        - JSONDecodeError / ValueError beim Parsen -> ParseError
        - 5xx Statuscodes -> NetworkError
        Sonst: Fehler unverändert zurückgeben.
        """
        # requests-spezifische Fehler erkennen, ohne harte Abhängigkeit zu erzwingen
        mod = getattr(err, "__module__", "")
        name = err.__class__.__name__.lower()
        msg = str(err).lower()

        # Hinweis auf Ratelimit
        if "rate limit" in msg or "ratelimit" in msg or "too many requests" in msg:
            return RateLimitError(str(err))

        # HTTP-Fehlercodes extrahieren, falls vorhanden
        status = None
        # Viele HTTP-Clientlibs exponieren "status" oder "status_code"
        status = getattr(err, "status", None) or getattr(err, "status_code", None)
        try:
            if status is not None:
                s = int(status)
                if s == 429:
                    return RateLimitError(str(err))
                if 500 <= s < 600 or s in (408, 503):  # 5xx und typische Transient-Codes
                    return NetworkError(str(err))
        except Exception:
            pass

        # requests Exceptions (falls installiert)
        if mod.startswith("requests"):
            if "timeout" in name or "connect" in name or "connection" in name:
                return NetworkError(str(err))

        # Parsing-Probleme (häufig nicht retrybar)
        # json.JSONDecodeError erbt von ValueError; wir detektieren beides über Nachricht
        if "expecting" in msg and "delimiter" in msg or "jsondecode" in name or "json" in msg and "decode" in msg:
            return ParseError(str(err))
        if isinstance(err, ValueError) and ("json" in msg or "parse" in msg):
            return ParseError(str(err))

        return err


__all__ = [
    "RetryStrategy",
    "RetryConfig",
    "RetryableError",
    "RateLimitError",
    "NetworkError",
    "ParseError",
]
