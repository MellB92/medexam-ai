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
        # Provider configuration with priority, budget, and model details
        # Priorität (1 = zuerst): Requesty > Anthropic > AWS Bedrock > Comet API > Perplexity > OpenRouter > OpenAI
        providers = {
            'requesty': {
                'api_key': os.getenv('REQUESTY_API_KEY'),
                'base_url': os.getenv('REQUESTY_BASE_URL', 'https://api.requesty.ai/v1'),
                'model': os.getenv('REQUESTY_MODEL', 'claude-sonnet'),
                'priority': 1,
                'budget': float(os.getenv('REQUESTY_BUDGET', '69.95')),
            },
            'comet': {
                'api_key': os.getenv('COMET_API_KEY'),
                'base_url': os.getenv('COMET_API_BASE_URL', 'https://api.cometapi.com/v1'),
                'model': os.getenv('COMET_API_MODEL', 'comet-general'),
                'priority': 4,
                'budget': float(os.getenv('COMET_API_BUDGET', '8.65')),
            },
            'perplexity': {
                'api_key': os.getenv('PERPLEXITY_API_KEY_1'),
                'base_url': os.getenv('PERPLEXITY_BASE_URL', 'https://api.perplexity.ai'),
                'model': os.getenv('PERPLEXITY_MODEL', 'llama-3-sonar-large-32k-online'),
                'priority': 5,
                'budget': float(os.getenv('PERPLEXITY_BUDGET', '15.00')),
            },
            'openrouter': {
                'api_key': os.getenv('OPENROUTER_API_KEY'),
                'base_url': 'https://openrouter.ai/api/v1',
                'model': os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.1-70b-instruct'),
                'priority': 6,
                'usage_target': 0.90,
            },
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'base_url': 'https://api.openai.com/v1',
                'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                'priority': 7,
                'budget': float(os.getenv('OPENAI_BUDGET', '9.99')),
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'base_url': 'https://api.anthropic.com/v1',
                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet'),
                'priority': 2,
                'budget': float(os.getenv('ANTHROPIC_BUDGET', '37.62')),
            },
            'aws_bedrock': {
                'api_key': os.getenv('AWS_BEDROCK_API_KEY'),
                'region': os.getenv('AWS_REGION', 'us-east-1'),
                'model': os.getenv('AWS_BEDROCK_MODEL', 'claude-3-5-sonnet'),
                'priority': 3,
                'budget': float(os.getenv('AWS_BEDROCK_BUDGET', '24.00')),
            },
            'google_cloud': {  # MedGemma via Vertex (optional)
                'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
                'project': os.getenv('GOOGLE_CLOUD_PROJECT'),
                'model': os.getenv('MEDGEMMA_MODEL', 'med-gemma-7b'),
                'priority': 8,
                'budget': float(os.getenv('MEDGEMMA_BUDGET', '0.0')),
                'type': 'medgemma',
                'name': 'medgemma',
            },
        }
        
        # Filter out providers that don't have an API key or necessary config
        active_providers = {name: conf for name, conf in providers.items() if self._is_provider_configured(name, conf)}
        return active_providers

    def _is_provider_configured(self, name: str, config: Dict[str, Any]) -> bool:
        """Checks if a provider has the minimum required configuration."""
        if name == 'google_cloud':
            return config.get('credentials_path') and config.get('project')
        if name == 'aws_bedrock':
            return bool(config.get('api_key'))  # Simplified; actual AWS auth may differ
        return config.get('api_key') is not None

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
        if getattr(provider, "type", None) == "legacy":
            raise ProviderError(provider.name, "Legacy provider dispatch not implemented.")
        elif provider.type == "medgemma":
            return self._process_with_medgemma(provider, prompt, system_prompt, **kwargs)
        elif provider.type == "aws_bedrock":
            # Placeholder: Implement Bedrock client here
            raise ProviderError(provider.type, "AWS Bedrock client not implemented in this stub.")
        return ProcessingResult(
            success=False,
            provider=getattr(provider, "type", "unknown"),
            model=getattr(provider, "model", ""),
            response_text="",
            error=f"Provider type '{getattr(provider, 'type', 'unknown')}' not supported.",
            timestamp=datetime.now().isoformat(),
        )

    def chat_completion(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.5) -> Dict[str, Any]:
        """Performs a chat completion, trying providers in order of priority."""
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        last_error = None
        for provider in self.provider_order:
            if provider not in self.providers:
                continue
            
            try:
                logger.info(f"Attempting request with provider: {provider}")
                response_data = self._make_request(provider, payload)
                
                # Assuming OpenAI-like response structure
                input_tokens = self._get_token_count(prompt)
                output_text = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                output_tokens = self._get_token_count(output_text)
                
                self._update_cost(input_tokens, output_tokens, provider)

                return {
                    "provider": provider,
                    "response": output_text,
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}
                }
            except Exception as e:
                logger.info(f"Provider {provider} failed: {e}")
                last_error = e
        
        # If all providers fail, raise the last error
        raise ProviderError("all", f"All providers failed. Last error: {last_error}")

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
