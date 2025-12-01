import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path

import tiktoken
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Import from existing project modules (tolerant, da pdf_utils ggf. nicht vorhanden)
try:
    from core.pdf_utils import extract_text_from_file  # type: ignore
except Exception:  # pragma: no cover
    extract_text_from_file = None
try:
    from core.exam_formatter import format_to_exam_standard  # type: ignore
except Exception:  # pragma: no cover
    format_to_exam_standard = None

# Load environment variables from .env file
load_dotenv()

# --- Setup Logging ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Custom Exceptions ---
class ProviderError(Exception):
    """Custom exception for provider-related errors."""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")

class BudgetExceededError(Exception):
    """Raised when a session's cost exceeds its budget."""
    pass

class RateLimitError(ProviderError):
    """Custom exception for rate limit errors."""
    pass

# --- Main Unified API Client ---


class ProviderConfig:
    """Lightweight container that allows flexible provider metadata."""

    def __init__(self, **kwargs: Any) -> None:
        # Store all provided attributes directly for dot-access compatibility.
        self.__dict__.update(kwargs)

        # Align legacy "service" field with newer "type" usage when missing.
        if 'type' not in self.__dict__ and 'service' in self.__dict__:
            self.type = self.service

        # Ensure model attribute is always present to avoid attribute errors downstream.
        if 'model' not in self.__dict__:
            self.model = kwargs.get('model', '')

    def __repr__(self) -> str:
        return f"ProviderConfig({self.__dict__!r})"


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

class UnifiedAPIClient:
    """A unified client to manage multiple AI providers with fallback, cost tracking, and resilience."""

    def __init__(self, max_cost: Optional[float] = None, checkpoint_dir: str = "checkpoints"):
        """
        Initializes the UnifiedAPIClient.

        Args:
            max_cost: Optional maximum cost for the session. If exceeded, raises BudgetExceededError.
            checkpoint_dir: Directory to store checkpoint files.
        """
        self.providers = self._configure_providers()
        self.provider_order = sorted(self.providers, key=lambda p: self.providers[p].get('priority', 99))
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self.session_cost = 0.0
        self.session_requests = 0
        self.max_cost = max_cost
        
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

        logger.info(f"UnifiedAPIClient initialized with providers: {', '.join(self.provider_order)}")

    def _configure_providers(self) -> Dict[str, Any]:
        """Loads provider configurations from environment variables."""
        # Provider-Reihenfolge:
        # 1) Requesty (Primary) - Sonnet 4.5 via Bedrock
        # 2) Requesty Opus - Opus 4.5 via Anthropic (für High-Yield)
        # 3) Portkey/OpenRouter (Fallback) - wenn Requesty ausfällt
        providers = {
            'requesty': {
                'api_key': os.getenv('REQUESTY_API_KEY'),
                'base_url': 'https://router.requesty.ai/v1',
                'model': os.getenv('REQUESTY_MODEL', 'bedrock/claude-sonnet-4-5@us-east-1'),
                'priority': 1,
                'budget': float(os.getenv('REQUESTY_BUDGET', '69.95')),
                'type': 'requesty',
            },
            'requesty_opus': {
                'api_key': os.getenv('REQUESTY_API_KEY'),
                'base_url': 'https://router.requesty.ai/v1',
                'model': os.getenv('REQUESTY_OPUS_MODEL', 'anthropic/claude-opus-4-5'),
                'priority': 2,
                'budget': float(os.getenv('REQUESTY_BUDGET', '69.95')),
                'type': 'requesty',
            },
            'portkey_openrouter': {
                'api_key': os.getenv('PORTKEY_API_KEY'),
                'base_url': 'https://api.portkey.ai/v1',
                'model': '@kp2026/anthropic/claude-sonnet-4.5',
                'priority': 3,
                'budget': float(os.getenv('OPENROUTER_BUDGET', '5.78')),
                'type': 'portkey',
            },
        }

        # Filter out providers without API key
        active = {}
        for name, conf in providers.items():
            if conf.get('api_key'):
                active[name] = conf
        return active

    def _is_provider_configured(self, name: str, config: Dict[str, Any]) -> bool:
        """Checks if a provider has the minimum required configuration."""
        if name == 'google_cloud':
            return config.get('credentials_path') and config.get('project')
        if name in ('portkey', 'requesty', 'requesty_opus'):
            return bool(config.get('api_key'))
        return False

    def _get_token_count(self, text: str) -> int:
        """Calculates the number of tokens in a string."""
        return len(self.tokenizer.encode(text))

    def _update_cost(self, input_tokens: int, output_tokens: int, provider: str):
        """Updates the session cost based on provider-specific pricing."""
        # Placeholder for actual cost calculation logic
        # In a real scenario, this would fetch pricing from a config or API
        cost_per_input_token = 0.000003 # Example cost for Claude 3.5 Sonnet on OpenRouter
        cost_per_output_token = 0.000015
        
        request_cost = (input_tokens * cost_per_input_token) + (output_tokens * cost_per_output_token)
        self.session_cost += request_cost
        self.session_requests += 1
        
        logger.info(f"Request cost ({provider}): ${request_cost:.6f}. Session total: ${self.session_cost:.4f}")

        if self.max_cost is not None and self.session_cost > self.max_cost:
            raise BudgetExceededError(f"Session budget of ${self.max_cost} exceeded. Current cost: ${self.session_cost:.4f}")

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3), reraise=True)
    def _make_request(self, provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Makes a request to a given provider's API, with retry logic."""
        config = self.providers[provider]
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        # This is a generic OpenAI-compatible payload structure.
        # Real implementation would require adapters for each provider's specific API format.
        api_payload = {
            "model": config['model'],
            "messages": payload['messages'],
            "max_tokens": payload.get('max_tokens', 4096),
            "temperature": payload.get('temperature', 0.5),
        }

        try:
            response = requests.post(config['base_url'] + '/chat/completions', headers=headers, json=api_payload, timeout=120)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError(provider, f"Rate limit exceeded: {e.response.text}")
            else:
                raise ProviderError(provider, f"HTTP error: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise ProviderError(provider, f"Request failed: {e}")

    def _process_with_medgemma(self, provider: ProviderConfig, prompt: str, system_prompt: Optional[str], **kwargs) -> ProcessingResult:
        """Verarbeitet eine Anfrage mit MedGemma über Vertex AI."""
        logger.info(f"→ Verarbeite mit {provider.name} (Modell: {provider.model})")
        try:
            from vertexai.generative_models import GenerativeModel, Part
            model = GenerativeModel(provider.model)

            # Prompt zusammenbauen (Systemprompt optional)
            parts = []
            if system_prompt:
                parts.append(Part.from_text(f"Systemanweisung: {system_prompt}"))
            parts.append(Part.from_text(prompt))

            response = model.generate_content(parts)
            content = getattr(response, "text", "") or str(response)

            try:
                input_tokens = model.count_tokens(parts).total_tokens
            except Exception:
                input_tokens = 0
            try:
                output_tokens = model.count_tokens(content).total_tokens
            except Exception:
                output_tokens = 0

            cost = self._calculate_vertex_cost(provider.model, input_tokens, output_tokens)

            return ProcessingResult(
                success=True,
                provider=provider.type,
                model=provider.model,
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"❌ MedGemma FEHLER: {e}")
            return ProcessingResult(
                success=False,
                provider=provider.type,
                model=provider.model,
                response_text="",
                error=str(e),
                timestamp=datetime.now().isoformat(),
            )

    def _process_with_portkey(self, provider: ProviderConfig, prompt: str, system_prompt: Optional[str], **kwargs) -> ProcessingResult:
        """Verarbeitet eine Anfrage über Portkey SDK (für @kp2026/... Modelle)."""
        logger.info(f"→ Verarbeite mit Portkey SDK ({provider.model})")
        try:
            from portkey_ai import Portkey
            client = Portkey(api_key=provider.api_key, base_url="https://api.portkey.ai/v1")

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=provider.model,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 1024),
                temperature=kwargs.get("temperature", 0.3),
            )

            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            self._update_cost(input_tokens, output_tokens, "portkey")

            return ProcessingResult(
                success=True,
                provider="portkey",
                model=provider.model,
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=self.session_cost,
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"❌ Portkey FEHLER: {e}")
            return ProcessingResult(
                success=False,
                provider="portkey",
                model=provider.model,
                response_text="",
                error=str(e),
                timestamp=datetime.now().isoformat(),
            )

    def _process_with_requesty(self, provider: ProviderConfig, prompt: str, system_prompt: Optional[str], **kwargs) -> ProcessingResult:
        """Verarbeitet eine Anfrage über Requesty (OpenAI-kompatibel)."""
        logger.info(f"→ Verarbeite mit Requesty ({provider.model})")
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": provider.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.3),
        }
        try:
            resp = requests.post(
                provider.base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            input_tokens = self._get_token_count(prompt)
            output_tokens = self._get_token_count(content)
            self._update_cost(input_tokens, output_tokens, "requesty")
            return ProcessingResult(
                success=True,
                provider="requesty",
                model=provider.model,
                response_text=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=self.session_cost,
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"❌ Requesty FEHLER: {e}")
            return ProcessingResult(
                success=False,
                provider="requesty",
                model=provider.model,
                response_text="",
                error=str(e),
                timestamp=datetime.now().isoformat(),
            )

    def _calculate_vertex_cost(self, model_name: str, in_tokens: int, out_tokens: int) -> float:
        PRICING_PER_1K = {
            "med-gemma-2b": (0.00010, 0.00040),
            "med-gemma-7b": (0.00020, 0.00080),
        }
        in_rate, out_rate = PRICING_PER_1K.get(model_name, (0.0, 0.0))
        return round((in_tokens/1000.0)*in_rate + (out_tokens/1000.0)*out_rate, 6)

    def _call_provider(
        self,
        provider: ProviderConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> ProcessingResult:
        """Ruft den passenden Provider auf basierend auf Typ."""
        ptype = getattr(provider, "type", "unknown")

        if ptype == "requesty":
            return self._process_with_requesty(provider, prompt, system_prompt, **kwargs)
        if ptype == "portkey":
            return self._process_with_portkey(provider, prompt, system_prompt, **kwargs)

        return ProcessingResult(
            success=False,
            provider=ptype,
            model=getattr(provider, "model", ""),
            response_text="",
            error=f"Provider type '{ptype}' not supported.",
            timestamp=datetime.now().isoformat(),
        )

    def chat_completion(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.5, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Performs a chat completion, trying providers in order of priority."""
        last_error = None
        for provider_name in self.provider_order:
            if provider_name not in self.providers:
                continue

            try:
                logger.info(f"Attempting request with provider: {provider_name}")
                config = self.providers[provider_name]

                # Erstelle ProviderConfig für _call_provider
                provider_config = ProviderConfig(
                    name=provider_name,
                    api_key=config.get('api_key'),
                    base_url=config.get('base_url'),
                    model=config.get('model'),
                    type=config.get('type'),
                )

                # Nutze das unified routing über _call_provider
                result = self._call_provider(
                    provider_config,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                if result.success:
                    return {
                        "provider": provider_name,
                        "response": result.response_text,
                        "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
                    }
                else:
                    logger.warning(f"Provider {provider_name} returned error: {result.error}")
                    last_error = result.error

            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_error = e

        # If all providers fail, raise the last error
        raise ProviderError("all", f"All providers failed. Last error: {last_error}")

    def complete(self, prompt: str, provider: str = None, model: str = None,
                 max_tokens: int = 2048, temperature: float = 0.3) -> Dict[str, Any]:
        """
        Convenience method for generate_answers.py compatibility.

        Calls chat_completion and parses JSON response for 5-Punkte-Schema fields.

        Args:
            prompt: The prompt to send to the LLM
            provider: Optional specific provider (ignored, uses priority order)
            model: Optional specific model (ignored, uses provider config)
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation

        Returns:
            Dict with parsed JSON fields or empty dict on error
        """
        try:
            result = self.chat_completion(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            response_text = result.get("response", "")

            # Try to parse JSON from response
            # Handle markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # Try to parse as JSON
            try:
                parsed = json.loads(response_text)
                return parsed
            except json.JSONDecodeError:
                # Try to find JSON object in response
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass

                logger.warning(f"Could not parse JSON from response: {response_text[:200]}...")
                return {}

        except Exception as e:
            logger.error(f"complete() failed: {e}")
            return {}

    # --- Integration with existing modules ---

    def process_pdf_with_api(self, pdf_path: str, prompt: str) -> dict:
        """Extracts text from a PDF and uses it in an API call."""
        try:
            text, _ = extract_text_from_file(pdf_path)
            if not text:
                return {"error": "Failed to extract text from PDF."}
            
            # Construct a more informative prompt
            combined_prompt = f"{prompt}\n\n--- Document Content ---\n{text[:8000]}..."
            
            return self.chat_completion(prompt=combined_prompt)
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return {"error": str(e)}

    def format_exam_questions(self, questions: list) -> str:
        """Uses exam_formatter.py to format a list of questions."""
        # This function seems to be more about local formatting than API calls.
        # Let's assume we want to format a list of raw text questions into the standard.
        formatted_texts = []
        for q_text in questions:
            try:
                # Here we use the local formatter, not an API call.
                formatted_q = format_to_exam_standard(q_text)
                formatted_texts.append(formatted_q)
            except Exception as e:
                logger.error(f"Failed to format question: {e}")
                formatted_texts.append(f"---\nERROR FORMATTING QUESTION:\n{q_text[:200]}...\n---")
        return "\n\n".join(formatted_texts)

    # --- Checkpoint System for Batch Processing ---

    def _save_checkpoint(self, checkpoint_file: str, state: Dict[str, Any]):
        """Saves the current batch processing state to a checkpoint file."""
        path = self.checkpoint_dir / checkpoint_file
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Checkpoint saved to {path}")

    def _load_checkpoint(self, checkpoint_file: str) -> Optional[Dict[str, Any]]:
        """Loads a batch processing state from a checkpoint file."""
        path = self.checkpoint_dir / checkpoint_file
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                state = json.load(f)
                logger.info(f"Checkpoint loaded from {path}")
                return state
        return None

    def batch_process_pdfs(self, pdf_dir: str, prompt_template: str, checkpoint_file: str = "batch_checkpoint.json") -> list:
        """Processes a directory of PDFs in a batch, with checkpointing."""
        pdf_paths = list(Path(pdf_dir).glob("*.pdf"))
        results = []
        
        # Load checkpoint if it exists
        checkpoint = self._load_checkpoint(checkpoint_file)
        start_index = checkpoint.get('last_processed_index', -1) + 1 if checkpoint else 0
        if checkpoint and 'results' in checkpoint:
            results = checkpoint['results']

        if start_index > 0:
            logger.info(f"Resuming batch process from index {start_index}")

        for i in range(start_index, len(pdf_paths)):
            pdf_path = pdf_paths[i]
            logger.info(f"Processing file {i+1}/{len(pdf_paths)}: {pdf_path.name}")
            
            try:
                # Here we use the integrated method
                result = self.process_pdf_with_api(str(pdf_path), prompt=prompt_template.format(filename=pdf_path.name))
                results.append({"file": pdf_path.name, "result": result})
                
                # Save checkpoint after each successful processing
                state = {'last_processed_index': i, 'results': results}
                self._save_checkpoint(checkpoint_file, state)

            except BudgetExceededError as e:
                logger.info(f"Budget exceeded. Stopping batch process. {e}")
                break # Stop the batch if budget is hit
            except Exception as e:
                logger.error(f"Failed to process {pdf_path.name}: {e}")
                # Optionally save partial failure to results
                results.append({"file": pdf_path.name, "result": {"error": str(e)}})
                state = {'last_processed_index': i, 'results': results}
                self._save_checkpoint(checkpoint_file, state)

        logger.info("Batch processing finished.")
        return results

    def get_cost_report(self) -> Dict[str, Any]:
        """Returns a summary of the session's cost and usage."""
        return {
            "total_cost": f"${self.session_cost:.4f}",
            "total_requests": self.session_requests
        }
