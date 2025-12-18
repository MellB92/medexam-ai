#!/usr/bin/env python3
"""
API Key Status Checker für MedExamAI
=====================================

Überprüft alle API-Keys und zeigt verfügbare Budgets an.

Verwendung:
    python3 scripts/check_api_keys.py --all
    python3 scripts/check_api_keys.py --provider requesty
    python3 scripts/check_api_keys.py --check-balance

Features:
- Validiert API-Keys (Verbindungstest)
- Ruft Live-Budget ab (wenn API unterstützt)
- Warnt bei niedrigen Budgets
- Exportiert Status-Report

Autor: MedExamAI Team
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

# Repo-Root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Lade .env
load_dotenv()

# Output-Verzeichnis
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "_OUTPUT"


class Colors:
    """ANSI Color Codes für Terminal-Output."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def check_requesty(api_key: str) -> Tuple[bool, Optional[float], str]:
    """
    Prüft Requesty API-Key und holt Balance.

    Returns:
        (is_valid, balance, message)
    """
    if not api_key:
        return False, None, "API Key nicht gesetzt"

    try:
        # Requesty verwendet OpenAI-kompatibles Format
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Minimale Test-Anfrage (ohne tatsächlichen LLM-Call)
        # Falls Requesty eine /models oder /account Endpoint hat:
        test_url = "https://api.requesty.ai/v1/models"

        response = requests.get(test_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # TODO: Balance-Endpoint finden (falls verfügbar)
            return True, None, "Valid (Balance-API nicht verfügbar)"
        elif response.status_code == 401:
            return False, None, "Unauthorized - Key ungültig"
        else:
            return False, None, f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def check_anthropic(api_key: str) -> Tuple[bool, Optional[float], str]:
    """Prüft Anthropic API-Key."""
    if not api_key:
        return False, None, "API Key nicht gesetzt"

    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

        # Anthropic hat keinen Balance-Endpoint, nur Test-Call
        # Wir machen KEINEN echten Call um Kosten zu sparen
        # Stattdessen: 401 = invalid, 400 = valid aber bad request
        test_url = "https://api.anthropic.com/v1/messages"

        response = requests.post(test_url, headers=headers, json={}, timeout=10)

        if response.status_code == 400:  # Bad request = Key ist valid
            return True, None, "Valid (Balance via Console prüfen)"
        elif response.status_code == 401:
            return False, None, "Unauthorized - Key ungültig"
        else:
            return False, None, f"HTTP {response.status_code}"

    except Exception as e:
        return False, None, f"Error: {str(e)}"


def check_openai(api_key: str) -> Tuple[bool, Optional[float], str]:
    """Prüft OpenAI API-Key und holt Balance."""
    if not api_key:
        return False, None, "API Key nicht gesetzt"

    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        # OpenAI /models Endpoint für Key-Validierung
        test_url = "https://api.openai.com/v1/models"

        response = requests.get(test_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # OpenAI hat keinen direkten Balance-Endpoint
            # User muss über Dashboard prüfen
            return True, None, "Valid (Balance via Dashboard prüfen)"
        elif response.status_code == 401:
            return False, None, "Unauthorized - Key ungültig"
        else:
            return False, None, f"HTTP {response.status_code}"

    except Exception as e:
        return False, None, f"Error: {str(e)}"


def check_perplexity(api_key: str) -> Tuple[bool, Optional[float], str]:
    """Prüft Perplexity API-Key."""
    if not api_key:
        return False, None, "API Key nicht gesetzt"

    try:
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        # Perplexity ist OpenAI-kompatibel
        test_url = "https://api.perplexity.ai/chat/completions"

        # Minimale Test-Anfrage
        payload = {
            "model": "llama-3-sonar-small-32k-online",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1
        }

        response = requests.post(test_url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            return True, None, "Valid (Balance via Dashboard prüfen)"
        elif response.status_code == 401:
            return False, None, "Unauthorized - Key ungültig"
        else:
            return False, None, f"HTTP {response.status_code}"

    except Exception as e:
        return False, None, f"Error: {str(e)}"


def check_openrouter(api_key: str) -> Tuple[bool, Optional[float], str]:
    """Prüft OpenRouter API-Key und holt Balance."""
    if not api_key:
        return False, None, "API Key nicht gesetzt"

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/medexamenai",
            "X-Title": "MedExamAI"
        }

        # OpenRouter /auth/key Endpoint
        test_url = "https://openrouter.ai/api/v1/auth/key"

        response = requests.get(test_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            balance = data.get("data", {}).get("limit_remaining")

            if balance is not None:
                return True, float(balance), "Valid"
            else:
                return True, None, "Valid (Balance nicht verfügbar)"
        elif response.status_code == 401:
            return False, None, "Unauthorized - Key ungültig"
        else:
            return False, None, f"HTTP {response.status_code}"

    except Exception as e:
        return False, None, f"Error: {str(e)}"


# Provider Mapping
PROVIDERS = {
    "requesty": {
        "env_var": "REQUESTY_API_KEY",
        "check_func": check_requesty,
        "budget_config": 69.95
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "check_func": check_anthropic,
        "budget_config": 37.62
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "check_func": check_openai,
        "budget_config": 9.99
    },
    "perplexity": {
        "env_var": "PERPLEXITY_API_KEY_1",
        "check_func": check_perplexity,
        "budget_config": 15.00
    },
    "openrouter": {
        "env_var": "OPENROUTER_API_KEY",
        "check_func": check_openrouter,
        "budget_config": 5.78
    }
}


def print_status(provider: str, is_valid: bool, balance: Optional[float], message: str, budget_config: float):
    """Druckt formatiertem Status für einen Provider."""
    icon = f"{Colors.GREEN}✅{Colors.RESET}" if is_valid else f"{Colors.RED}❌{Colors.RESET}"

    balance_str = ""
    if balance is not None:
        if balance < 5.0:
            balance_str = f"{Colors.RED}${balance:.2f} (KRITISCH!){Colors.RESET}"
        elif balance < 20.0:
            balance_str = f"{Colors.YELLOW}${balance:.2f} (Niedrig){Colors.RESET}"
        else:
            balance_str = f"{Colors.GREEN}${balance:.2f}{Colors.RESET}"
    else:
        balance_str = f"{Colors.BLUE}Config: ${budget_config:.2f}{Colors.RESET}"

    print(f"{icon} {Colors.BOLD}{provider.upper():15}{Colors.RESET} | {message:40} | Balance: {balance_str}")


def check_all_providers(verbose: bool = False) -> Dict[str, Dict]:
    """Prüft alle Provider und gibt Ergebnisse zurück."""
    results = {}

    print(f"\n{Colors.BOLD}{'='*90}{Colors.RESET}")
    print(f"{Colors.BOLD}MedExamAI API Key Status Check{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*90}{Colors.RESET}\n")

    for provider, config in PROVIDERS.items():
        env_var = config["env_var"]
        check_func = config["check_func"]
        budget_config = config["budget_config"]

        api_key = os.getenv(env_var)

        if verbose and api_key:
            print(f"Prüfe {provider}... (Key: {api_key[:10]}...)")

        is_valid, balance, message = check_func(api_key)

        results[provider] = {
            "valid": is_valid,
            "balance": balance,
            "message": message,
            "budget_config": budget_config,
            "env_var": env_var
        }

        print_status(provider, is_valid, balance, message, budget_config)

    print(f"\n{Colors.BOLD}{'='*90}{Colors.RESET}\n")

    return results


def export_report(results: Dict[str, Dict], output_file: Path):
    """Exportiert Status-Report als JSON."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_providers": len(results),
        "valid_keys": sum(1 for r in results.values() if r["valid"]),
        "invalid_keys": sum(1 for r in results.values() if not r["valid"]),
        "total_balance": sum(r["balance"] for r in results.values() if r["balance"] is not None),
        "providers": results
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"{Colors.GREEN}✅ Report gespeichert: {output_file}{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="API Key Status Checker für MedExamAI")
    parser.add_argument("--all", action="store_true", help="Alle Provider prüfen")
    parser.add_argument("--provider", type=str, choices=list(PROVIDERS.keys()),
                       help="Einzelnen Provider prüfen")
    parser.add_argument("--check-balance", action="store_true", help="Live-Balance abrufen (wo verfügbar)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose Output")
    parser.add_argument("--export", type=str, help="Export Report als JSON")

    args = parser.parse_args()

    if not any([args.all, args.provider, args.check_balance]):
        parser.print_help()
        sys.exit(1)

    if args.all or args.check_balance:
        results = check_all_providers(verbose=args.verbose)

        if args.export:
            export_file = Path(args.export)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = OUTPUT_DIR / f"api_key_status_{timestamp}.json"

        export_report(results, export_file)

    elif args.provider:
        provider = args.provider
        config = PROVIDERS[provider]
        api_key = os.getenv(config["env_var"])

        print(f"\n{Colors.BOLD}Prüfe {provider.upper()}...{Colors.RESET}\n")

        is_valid, balance, message = config["check_func"](api_key)
        print_status(provider, is_valid, balance, message, config["budget_config"])

        if not is_valid:
            sys.exit(1)


if __name__ == "__main__":
    main()

