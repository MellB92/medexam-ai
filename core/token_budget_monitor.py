"""Lightweight token and cost tracking with provider-aware budgets."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class ProviderBudget:
    """Runtime counters for a single provider."""

    budget_limit: Optional[float] = None
    rate_in: float = 0.0
    rate_out: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    requests: int = 0

    def add_usage(self, input_tokens: int, output_tokens: int, cost: float) -> float:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost += cost
        self.requests += 1
        return self.cost

    @property
    def tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TokenBudgetMonitor:
    """Tracks token usage and costs per provider and session."""

    def __init__(
        self,
        budget_limit: Optional[float] = None,
        pricing: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> None:
        """
        Args:
            budget_limit: Optional global budget for the session (USD).
            pricing: Optional map of provider -> (input_per_1k, output_per_1k).
        """
        self.budget_limit = float(budget_limit) if budget_limit is not None else None
        self.pricing = pricing or {}
        self.providers: Dict[str, ProviderBudget] = {}
        self.total_cost = 0.0
        self.total_tokens = 0

    def register_provider(
        self,
        name: str,
        budget_limit: Optional[float] = None,
        rates: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Register a provider for tracking."""
        in_rate, out_rate = rates if rates else (0.0, 0.0)
        self.providers[name] = ProviderBudget(
            budget_limit=None if budget_limit is None else float(budget_limit),
            rate_in=in_rate,
            rate_out=out_rate,
        )

    def estimate_tokens(self, text: str, model: str = "cl100k_base") -> int:
        """Rough token estimation using tiktoken (falls back to len/4)."""
        try:
            encoder = tiktoken.get_encoding(model)
            return len(encoder.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _calc_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a call."""
        rates = self.pricing.get(provider)
        if rates:
            in_rate, out_rate = rates
        else:
            prov = self.providers.get(provider)
            in_rate, out_rate = (prov.rate_in, prov.rate_out) if prov else (0.0, 0.0)

        return (input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate

    def track_usage(
        self,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        cost_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Record usage and return a snapshot.

        Args:
            provider: Provider key.
            input_tokens: Prompt tokens.
            output_tokens: Completion tokens.
            cost_override: Optional externally computed cost.
        """
        if provider not in self.providers:
            self.register_provider(provider)

        provider_budget = self.providers[provider]
        cost = cost_override if cost_override is not None else self._calc_cost(
            provider, input_tokens, output_tokens
        )

        provider_budget.add_usage(input_tokens, output_tokens, cost)
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens

        logger.debug(
            "💰 %s: +%s tokens (+$%.4f) | Total $%.4f",
            provider,
            input_tokens + output_tokens,
            cost,
            self.total_cost,
        )

        return self.get_provider_stats(provider)

    def is_exhausted(self, provider: str) -> bool:
        """Check whether a provider budget is exhausted."""
        pb = self.providers.get(provider)
        if not pb or pb.budget_limit is None:
            return False
        return pb.cost >= pb.budget_limit

    def remaining_budget(self, provider: str) -> Optional[float]:
        """Return remaining budget for provider, or None if unlimited."""
        pb = self.providers.get(provider)
        if not pb or pb.budget_limit is None:
            return None
        return max(0.0, pb.budget_limit - pb.cost)

    def get_provider_stats(self, provider: str) -> Dict[str, Any]:
        """Return stats for a provider."""
        pb = self.providers.get(provider) or ProviderBudget()
        return {
            "budget_limit": pb.budget_limit,
            "remaining": self.remaining_budget(provider),
            "input_tokens": pb.input_tokens,
            "output_tokens": pb.output_tokens,
            "tokens": pb.tokens,
            "cost": pb.cost,
            "requests": pb.requests,
        }

    def summary(self) -> Dict[str, Any]:
        """Return a session level summary."""
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "budget_limit": self.budget_limit,
            "providers": {name: self.get_provider_stats(name) for name in self.providers},
        }
