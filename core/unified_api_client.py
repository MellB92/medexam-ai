import os
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import tiktoken
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# Optional imports - tolerant falls Module nicht vorhanden
try:  # pragma: no cover - optional helper
    from core.token_budget_monitor import TokenBudgetMonitor
except Exception:  # pragma: no cover - fallback
    TokenBudgetMonitor = None

try:  # pragma: no cover
    from core.pdf_utils import extract_text_from_file
except Exception:  # pragma: no cover
    extract_text_from_file = None

try:  # pragma: no cover
    from core.exam_formatter import format_to_exam_standard
except Exception:  # pragma: no cover
    format_to_exam_standard = None

load_dotenv()

# --- Setup Logging ---
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# --- Custom Exceptions ---
class ProviderError(Exception):
    """Custom exception for provider-related errors."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


class BudgetExceededError(Exception):
    """Raised when a session's cost exceeds its budget."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.provider = provider
        super().__init__(message)


class RateLimitError(ProviderError):
    """Custom exception for rate limit errors."""


# --- Data Models ---
@dataclass
class ProviderConfig:
    key: str
    name: str
    type: str
    adapter: str
    api_key: Optional[str]
    base_url: Optional[str]
    model: Optional[str]
    priority: int
    budget: Optional[float] = None
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_tokens: int = 4096
    timeout: int = 120


@dataclass
class ProcessingResult:
    success: bool
    provider: str
    model: str
    response_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None
    raw_response: Optional[Any] = None


class UnifiedAPIClient:
    """Manage multiple AI providers with fallback, budget-tracking and cost reporting."""

    DEFAULT_PRICING: Dict[str, Tuple[float, float]] = {
        "requesty": (3.0, 15.0),
        "anthropic": (3.0, 15.0),
        "aws_bedrock": (3.0, 15.0),
        "comet_api": (2.4, 12.0),
        "perplexity": (1.2, 1.2),
        "openrouter": (0.5, 1.5),
        "openai": (0.5, 1.5),
        "portkey": (3.0, 15.0),
        "medgemma": (0.1, 0.4),
    }

    DEFAULT_BUDGETS: Dict[str, float] = {
        "requesty": 69.95,
        "anthropic": 37.62,
        "aws_bedrock": 24.0,
        "comet_api": 8.65,
        "perplexity": 15.0,
        "openrouter": 5.78,
        "openai": 9.99,
        "medgemma": 217.75,
    }

    def __init__(self, max_cost: Optional[float] = None, checkpoint_dir: str = "checkpoints"):
        self.max_cost = max_cost
        self.pricing = dict(self.DEFAULT_PRICING)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Budget & cost state
        self.session_cost = 0.0
        self.session_requests = 0
        self.provider_spend: Dict[str, float] = {}

        # Optional global budget monitor
        self.budget_monitor = (
            TokenBudgetMonitor(budget_limit=max_cost, pricing=self.pricing)
            if TokenBudgetMonitor
            else None
        )

        self.providers = self._configure_providers()
        self.provider_order = [
            p.key for p in sorted(self.providers.values(), key=lambda c: c.priority)
        ]
        self.provider_spend = {p.key: 0.0 for p in self.providers.values()}

        if self.budget_monitor:
            for p in self.providers.values():
                self.budget_monitor.register_provider(
                    p.key,
                    budget_limit=p.budget,
                    rates=(p.cost_per_1k_input, p.cost_per_1k_output),
                )

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

        logger.info(
            "UnifiedAPIClient initialized with providers: %s",
            ", ".join(self.provider_order) if self.provider_order else "none",
        )

    # --- Provider Setup ---
    def _get_budget(self, env_var: str, default: float) -> float:
        try:
            return float(os.getenv(env_var, default))
        except ValueError:
            return default

    def _pricing_for_model(
        self, model: str, default: Tuple[float, float]
    ) -> Tuple[float, float]:
        if "opus" in model.lower():
            return (15.0, 75.0)
        return default

    def _configure_providers(self) -> Dict[str, ProviderConfig]:
        providers: Dict[str, ProviderConfig] = {}

        def add(cfg: ProviderConfig):
            if not cfg.api_key and cfg.adapter not in {"bedrock", "medgemma"}:
                return
            providers[cfg.key] = cfg

        budgets = self.DEFAULT_BUDGETS

        add(
            ProviderConfig(
                key="requesty",
                name="Requesty",
                type="requesty",
                adapter="openai",
                api_key=os.getenv("REQUESTY_API_KEY"),
                base_url=os.getenv("REQUESTY_BASE_URL", "https://router.requesty.ai/v1"),
                model=os.getenv("REQUESTY_MODEL", "bedrock/claude-sonnet-4-5@us-east-1"),
                priority=1,
                budget=self._get_budget("REQUESTY_BUDGET", budgets["requesty"]),
                cost_per_1k_input=3.0,
                cost_per_1k_output=15.0,
                max_tokens=32000,
            )
        )

        anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        anth_rates = self._pricing_for_model(anthropic_model, (3.0, 15.0))
        add(
            ProviderConfig(
                key="anthropic",
                name="Anthropic Direct",
                type="anthropic",
                adapter="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                base_url="https://api.anthropic.com/v1",
                model=anthropic_model,
                priority=2,
                budget=self._get_budget("ANTHROPIC_BUDGET", budgets["anthropic"]),
                cost_per_1k_input=anth_rates[0],
                cost_per_1k_output=anth_rates[1],
                max_tokens=32000,
            )
        )

        bedrock_env = (
            os.getenv("AWS_REGION")
            or os.getenv("AWS_PROFILE")
            or os.getenv("BEDROCK_ASSUME_ROLE")
        )
        if bedrock_env:
            add(
                ProviderConfig(
                    key="aws_bedrock",
                    name="AWS Bedrock",
                    type="aws_bedrock",
                    adapter="bedrock",
                    api_key=None,  # credentials via boto3/env
                    base_url=None,
                    model=os.getenv(
                        "AWS_BEDROCK_MODEL",
                        "anthropic.claude-3-5-sonnet-20241022-v2:0",
                    ),
                    priority=3,
                    budget=self._get_budget("AWS_BEDROCK_BUDGET", budgets["aws_bedrock"]),
                    cost_per_1k_input=3.0,
                    cost_per_1k_output=15.0,
                    max_tokens=32000,
                )
            )

        add(
            ProviderConfig(
                key="portkey",
                name="Portkey Gateway",
                type="portkey",
                adapter="openai",
                api_key=os.getenv("PORTKEY_API_KEY"),
                base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
                model=os.getenv("PORTKEY_MODEL", "@kp2026/anthropic/claude-sonnet-4.5"),
                priority=3,
                budget=self._get_budget("PORTKEY_BUDGET", budgets.get("aws_bedrock", 0.0)),
                cost_per_1k_input=3.0,
                cost_per_1k_output=15.0,
                max_tokens=32000,
            )
        )

        add(
            ProviderConfig(
                key="comet_api",
                name="Comet API",
                type="comet_api",
                adapter="openai",
                api_key=os.getenv("COMET_API_KEY"),
                base_url=os.getenv("COMET_API_BASE", "https://api.cometapi.com/v1"),
                model=os.getenv("COMET_API_MODEL", "claude-sonnet-4-5"),
                priority=4,
                budget=self._get_budget("COMET_API_BUDGET", budgets["comet_api"]),
                cost_per_1k_input=2.4,
                cost_per_1k_output=12.0,
                max_tokens=32000,
            )
        )

        pplx_key = (
            os.getenv("PERPLEXITY_API_KEY")
            or os.getenv("PERPLEXITY_API_KEY_1")
            or os.getenv("PERPLEXITY_API_KEY_2")
        )
        add(
            ProviderConfig(
                key="perplexity",
                name="Perplexity",
                type="perplexity",
                adapter="openai",
                api_key=pplx_key,
                base_url=os.getenv("PERPLEXITY_API_BASE", "https://api.perplexity.ai"),
                model=os.getenv(
                    "PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online"
                ),
                priority=5,
                budget=self._get_budget("PERPLEXITY_BUDGET", budgets["perplexity"]),
                cost_per_1k_input=1.2,
                cost_per_1k_output=1.2,
                max_tokens=8000,
            )
        )

        add(
            ProviderConfig(
                key="openrouter",
                name="OpenRouter",
                type="openrouter",
                adapter="openai",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                model=os.getenv("OPENROUTER_MODEL", "openai/o3-mini-high"),
                priority=6,
                budget=self._get_budget("OPENROUTER_BUDGET", budgets["openrouter"]),
                cost_per_1k_input=0.5,
                cost_per_1k_output=1.5,
                max_tokens=16000,
            )
        )

        add(
            ProviderConfig(
                key="openai",
                name="OpenAI",
                type="openai",
                adapter="openai",
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1",
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                priority=7,
                budget=self._get_budget("OPENAI_BUDGET", budgets["openai"]),
                cost_per_1k_input=0.5,
                cost_per_1k_output=1.5,
                max_tokens=16000,
            )
        )

        gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if gcp_creds and Path(gcp_creds).exists():
            add(
                ProviderConfig(
                    key="medgemma",
                    name="MedGemma (Vertex AI)",
                    type="medgemma",
                    adapter="medgemma",
                    api_key=None,
                    base_url=None,
                    model=os.getenv("MEDGEMMA_MODEL", "med-gemma-7b"),
                    priority=8,
                    budget=self._get_budget("MEDGEMMA_BUDGET", budgets["medgemma"]),
                    cost_per_1k_input=0.1,
                    cost_per_1k_output=0.4,
                    max_tokens=4096,
                )
            )

        return providers

    # --- Helpers ---
    def _get_token_count(self, text: str) -> int:
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _build_messages(self, prompt: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _calculate_cost(self, cfg: ProviderConfig, input_tokens: int, output_tokens: int) -> float:
        in_rate = cfg.cost_per_1k_input or self.pricing.get(cfg.key, (0.0, 0.0))[0]
        out_rate = cfg.cost_per_1k_output or self.pricing.get(cfg.key, (0.0, 0.0))[1]
        return (input_tokens / 1000.0) * in_rate + (output_tokens / 1000.0) * out_rate

    def _budget_remaining(self, cfg: ProviderConfig) -> Optional[float]:
        if cfg.budget is None:
            return None
        spent = self.provider_spend.get(cfg.key, 0.0)
        return max(0.0, cfg.budget - spent)

    def _is_budget_exhausted(self, cfg: ProviderConfig) -> bool:
        if cfg.budget is not None and self.provider_spend.get(cfg.key, 0.0) >= cfg.budget:
            return True
        if self.budget_monitor and self.budget_monitor.is_exhausted(cfg.key):
            return True
        return False

    def _record_cost(self, cfg: ProviderConfig, input_tokens: int, output_tokens: int) -> float:
        cost = self._calculate_cost(cfg, input_tokens, output_tokens)
        self.session_cost += cost
        self.session_requests += 1
        self.provider_spend[cfg.key] = self.provider_spend.get(cfg.key, 0.0) + cost

        if self.budget_monitor:
            self.budget_monitor.track_usage(
                cfg.key, input_tokens, output_tokens, cost_override=cost
            )

        if self.max_cost is not None and self.session_cost > self.max_cost:
            raise BudgetExceededError(
                f"Session budget ${self.max_cost:.2f} exceeded (now ${self.session_cost:.2f})",
                provider="session",
            )
        return cost

    def _build_order(self, preferred_provider: Optional[str]) -> List[str]:
        if preferred_provider and preferred_provider in self.providers:
            remaining = [p for p in self.provider_order if p != preferred_provider]
            return [preferred_provider] + remaining
        return list(self.provider_order)

    # --- Provider Call Implementations ---
    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
    def _post_with_retry(
        self, url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int
    ) -> requests.Response:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 429:
            raise RateLimitError("rate_limit", f"429: {resp.text}")
        resp.raise_for_status()
        return resp

    def _call_openai_style(
        self,
        cfg: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        override_model: Optional[str],
    ) -> ProcessingResult:
        messages = self._build_messages(prompt, system_prompt)
        payload = {
            "model": override_model or cfg.model,
            "messages": messages,
            "max_tokens": min(max_tokens, cfg.max_tokens),
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        if cfg.key == "openrouter":
            headers["HTTP-Referer"] = "https://medexamen.ai"
            headers["X-Title"] = "MedExamAI"

        try:
            response = self._post_with_retry(
                cfg.base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                payload=payload,
                timeout=cfg.timeout,
            )
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            usage = data.get("usage", {}) or {}
            input_tokens = usage.get("prompt_tokens") or self._get_token_count(
                prompt + (system_prompt or "")
            )
            output_tokens = usage.get("completion_tokens") or self._get_token_count(
                content or ""
            )
            cost = self._record_cost(cfg, input_tokens, output_tokens)

            return ProcessingResult(
                success=True,
                provider=cfg.key,
                model=override_model or cfg.model or "",
                response_text=content or "",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                timestamp=datetime.now().isoformat(),
                raw_response=data,
            )
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.warning("Provider %s failed: %s", cfg.key, e)
            return ProcessingResult(
                success=False,
                provider=cfg.key,
                model=override_model or cfg.model or "",
                response_text="",
                error=str(e),
            )

    def _call_anthropic(
        self,
        cfg: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> ProcessingResult:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=cfg.api_key)
            resp = client.messages.create(
                model=cfg.model,
                max_tokens=min(max_tokens, cfg.max_tokens),
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                system=system_prompt,
            )
            content = "".join(part.text for part in resp.content if hasattr(part, "text"))
            usage = getattr(resp, "usage", None) or {}
            input_tokens = getattr(usage, "input_tokens", None) or self._get_token_count(
                prompt + (system_prompt or "")
            )
            output_tokens = getattr(usage, "output_tokens", None) or self._get_token_count(
                content
            )
            cost = self._record_cost(cfg, input_tokens, output_tokens)
            return ProcessingResult(
                success=True,
                provider=cfg.key,
                model=cfg.model or "",
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                timestamp=datetime.now().isoformat(),
                raw_response=resp,
            )
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.warning("Anthropic call failed: %s", e)
            return ProcessingResult(
                success=False,
                provider=cfg.key,
                model=cfg.model or "",
                response_text="",
                error=str(e),
            )

    def _call_bedrock(
        self,
        cfg: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> ProcessingResult:
        try:
            import boto3

            client = boto3.client("bedrock-runtime")
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            system = [{"text": system_prompt}] if system_prompt else None
            resp = client.converse(
                modelId=cfg.model,
                messages=messages,
                system=system,
                inferenceConfig={
                    "maxTokens": min(max_tokens, cfg.max_tokens),
                    "temperature": temperature,
                },
            )
            content_parts = resp.get("output", {}).get("message", {}).get("content", [])
            content = "".join(part.get("text", "") for part in content_parts)
            usage = resp.get("usage", {}) or {}
            input_tokens = (
                usage.get("inputTokens")
                or usage.get("input_tokens")
                or self._get_token_count(prompt + (system_prompt or ""))
            )
            output_tokens = (
                usage.get("outputTokens")
                or usage.get("output_tokens")
                or self._get_token_count(content)
            )
            cost = self._record_cost(cfg, input_tokens, output_tokens)
            return ProcessingResult(
                success=True,
                provider=cfg.key,
                model=cfg.model or "",
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                timestamp=datetime.now().isoformat(),
                raw_response=resp,
            )
        except BudgetExceededError:
            raise
        except Exception as e:
            logger.warning("Bedrock call failed: %s", e)
            return ProcessingResult(
                success=False,
                provider=cfg.key,
                model=cfg.model or "",
                response_text="",
                error=str(e),
            )

    def _process_with_medgemma(
        self,
        cfg: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> ProcessingResult:
        logger.info("→ Verarbeite mit %s (Modell: %s)", cfg.name, cfg.model)
        try:
            from vertexai.generative_models import GenerativeModel, Part

            model = GenerativeModel(cfg.model)
            parts = []
            if system_prompt:
                parts.append(Part.from_text(f"Systemanweisung: {system_prompt}"))
            parts.append(Part.from_text(prompt))

            response = model.generate_content(
                parts,
                generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
            )
            content = getattr(response, "text", "") or str(response)
            try:
                input_tokens = model.count_tokens(parts).total_tokens
            except Exception:
                input_tokens = 0
            try:
                output_tokens = model.count_tokens(content).total_tokens
            except Exception:
                output_tokens = 0
            cost = self._calculate_cost(cfg, input_tokens, output_tokens)
            if self.budget_monitor:
                self.budget_monitor.track_usage(
                    cfg.key, input_tokens, output_tokens, cost_override=cost
                )
            self.session_cost += cost
            return ProcessingResult(
                success=True,
                provider=cfg.key,
                model=cfg.model or "",
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                timestamp=datetime.now().isoformat(),
                raw_response=response,
            )
        except Exception as e:
            logger.error("❌ MedGemma FEHLER: %s", e)
            return ProcessingResult(
                success=False,
                provider=cfg.key,
                model=cfg.model or "",
                response_text="",
                error=str(e),
            )

    def _call_provider(
        self,
        cfg: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        override_model: Optional[str],
    ) -> ProcessingResult:
        if cfg.adapter == "openai":
            return self._call_openai_style(
                cfg, prompt, system_prompt, max_tokens, temperature, override_model
            )
        if cfg.adapter == "anthropic":
            return self._call_anthropic(cfg, prompt, system_prompt, max_tokens, temperature)
        if cfg.adapter == "bedrock":
            return self._call_bedrock(cfg, prompt, system_prompt, max_tokens, temperature)
        if cfg.adapter == "medgemma":
            return self._process_with_medgemma(cfg, prompt, system_prompt, max_tokens, temperature)

        return ProcessingResult(
            success=False,
            provider=cfg.key,
            model=cfg.model or "",
            response_text="",
            error=f"Provider type '{cfg.adapter}' not supported.",
        )

    # --- Public API ---
    def chat_completion(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.5,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Performs a chat completion, trying providers in order of priority."""
        last_error: Any = None

        for provider_key in self._build_order(provider):
            cfg = self.providers.get(provider_key)
            if not cfg:
                continue

            if self._is_budget_exhausted(cfg):
                logger.info("Skipping %s: budget exhausted", cfg.key)
                last_error = f"{cfg.key} budget exhausted"
                continue

            logger.info("Attempting request with provider: %s", cfg.key)
            try:
                result = self._call_provider(
                    cfg,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    override_model=model,
                )
            except BudgetExceededError:
                raise
            except Exception as e:
                last_error = e
                continue

            if result.success:
                usage = {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost": result.cost,
                }
                return {
                    "provider": cfg.key,
                    "model": result.model,
                    "response": result.response_text,
                    "usage": usage,
                    "meta": {
                        "timestamp": result.timestamp,
                        "budget_remaining": self._budget_remaining(cfg),
                    },
                }

            last_error = result.error

        raise ProviderError(provider or "all", f"All providers failed. Last error: {last_error}")

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            text = text[json_start:json_end].strip()
        elif "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            text = text[json_start:json_end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start_idx = text.find("{")
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(text[start_idx:], start_idx):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                try:
                    return json.loads(text[start_idx:end_idx])
                except Exception:
                    return None
        return None

    def complete(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper: performs a chat completion and tries to parse JSON payloads.
        Returns parsed fields plus __meta__ for downstream budget tracking.
        """
        try:
            result = self.chat_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
                provider=provider,
                model=model,
            )
            response_text = result.get("response", "")
            parsed = self._extract_json_object(response_text) or {}
            parsed["__meta__"] = {
                "provider": result.get("provider"),
                "model": result.get("model"),
                "usage": result.get("usage", {}),
                "cost": result.get("usage", {}).get("cost", 0.0),
                "budget_remaining": result.get("meta", {}).get("budget_remaining"),
                "raw_response": response_text,
            }
            return parsed
        except BudgetExceededError:
            raise
        except ProviderError:
            raise
        except Exception as e:
            logger.error("complete() failed: %s", e)
            return {}

    # --- Integration Helpers ---
    def process_pdf_with_api(self, pdf_path: str, prompt: str) -> dict:
        """Extract text from PDF and pass into a chat completion."""
        if extract_text_from_file is None:
            return {"error": "pdf_utils not available"}
        try:
            text, _ = extract_text_from_file(pdf_path)
            if not text:
                return {"error": "Failed to extract text from PDF."}

            combined_prompt = f"{prompt}\n\n--- Document Content ---\n{text[:8000]}..."
            return self.chat_completion(prompt=combined_prompt)
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {"error": str(e)}

    def format_exam_questions(self, questions: List[str]) -> str:
        """Format a list of questions via exam_formatter (local helper)."""
        if format_to_exam_standard is None:
            return "\n\n".join(questions)

        formatted_texts = []
        for q_text in questions:
            try:
                formatted_q = format_to_exam_standard(q_text)
                formatted_texts.append(formatted_q)
            except Exception as e:
                logger.error(f"Failed to format question: {e}")
                formatted_texts.append(
                    f"---\nERROR FORMATTING QUESTION:\n{q_text[:200]}...\n---"
                )
        return "\n\n".join(formatted_texts)

    # --- Checkpoint System for batch jobs (legacy compatibility) ---
    def _save_checkpoint(self, checkpoint_file: str, state: Dict[str, Any]):
        path = self.checkpoint_dir / checkpoint_file
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info("Checkpoint saved to %s", path)

    def _load_checkpoint(self, checkpoint_file: str) -> Optional[Dict[str, Any]]:
        path = self.checkpoint_dir / checkpoint_file
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
                logger.info("Checkpoint loaded from %s", path)
                return state
        return None

    def batch_process_pdfs(
        self, pdf_dir: str, prompt_template: str, checkpoint_file: str = "batch_checkpoint.json"
    ) -> list:
        """Processes PDFs in a directory with checkpointing support."""
        pdf_paths = list(Path(pdf_dir).glob("*.pdf"))
        results = []
        checkpoint = self._load_checkpoint(checkpoint_file)
        start_index = checkpoint.get("last_processed_index", -1) + 1 if checkpoint else 0
        if checkpoint and "results" in checkpoint:
            results = checkpoint["results"]

        for i in range(start_index, len(pdf_paths)):
            pdf_path = pdf_paths[i]
            logger.info("Processing file %s/%s: %s", i + 1, len(pdf_paths), pdf_path.name)
            try:
                result = self.process_pdf_with_api(
                    str(pdf_path), prompt=prompt_template.format(filename=pdf_path.name)
                )
                results.append({"file": pdf_path.name, "result": result})
                state = {"last_processed_index": i, "results": results}
                self._save_checkpoint(checkpoint_file, state)
            except BudgetExceededError as e:
                logger.info("Budget exceeded. Stopping batch process. %s", e)
                break
            except Exception as e:
                logger.error("Failed to process %s: %s", pdf_path.name, e)
                results.append({"file": pdf_path.name, "result": {"error": str(e)}})
                state = {"last_processed_index": i, "results": results}
                self._save_checkpoint(checkpoint_file, state)

        logger.info("Batch processing finished.")
        return results

    def get_cost_report(self) -> Dict[str, Any]:
        return {
            "total_cost": round(self.session_cost, 4),
            "total_requests": self.session_requests,
            "provider_spend": self.provider_spend,
            "budget_summary": self.budget_monitor.summary() if self.budget_monitor else {},
        }
