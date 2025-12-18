# 🏆 CODEX MEGA-PROMPT: MedExamAI Production Pipeline v3.0

**Mit:** Perplexity+Portkey RAG | Gold Standard Validierung | Medical Validation Layer
**Kritisch für:** Kenntnisprüfung März 2026

---

## 📐 DAS PYRAMIDEN-SYSTEM

```
                    ┌─────────────┐
                    │   TIER 1    │  ◀── _GOLD_STANDARD/
                    │ Prüfungs-   │      Echte Protokolle
                    │ protokolle  │      = ABSOLUTE WAHRHEIT
                    │  (16,725)   │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │         TIER 2          │  ◀── Innere_Medizin/, etc.
              │   Lehrbücher/Leitlinien │      Hintergrundwissen
              │   (Ergänzung wenn T1    │      = SUPPORT
              │    keine Antwort hat)   │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   MEDICAL VALIDATION    │
              │   LAYER (4 Prüfer)      │
              │   ────────────────────  │
              │   💊 Dosage Validator   │
              │   📋 ICD-10 Validator   │
              │   🧪 Lab Value Valid.   │
              │   🧠 Logical Consist.   │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │   ✅ VALIDIERTE Q&A     │
              │   oder                  │
              │   🔒 QUARANTÄNE         │
              └─────────────────────────┘
```

---

## 🎯 ZIELE DIESER PHASE

| Ziel | Beschreibung | Erfolgsmetrik |
|------|--------------|---------------|
| **RAG 100%** | Perplexity+Portkey vollständig integriert | Alle Queries funktionieren |
| **Gold Standard Match** | Generierte Q&A gegen Protokolle validieren | >80% Übereinstimmung |
| **Lücken-Analyse** | Was fehlt in unseren 3,170 Q&A? | Liste der fehlenden Themen |
| **Medical Validation** | 4 Prüfer durchlaufen | <5% Quarantäne-Rate |

---

# 🔧 TEIL 1: PERPLEXITY + PORTKEY RAG (100% KOMPLETT)

## 1.1 Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PORTKEY GATEWAY                                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Features:                                                     │   │
│  │ • Load Balancing zwischen 2 Perplexity Keys                  │   │
│  │ • Automatisches Retry bei Fehlern                            │   │
│  │ • Response Caching (spart Kosten!)                           │   │
│  │ • Request Logging für Debugging                              │   │
│  │ • Budget Tracking (max €5/Session)                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │ PERPLEXITY_KEY_1│◀──▶│ PERPLEXITY_KEY_2│  (Failover)            │
│  └─────────────────┘    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

## 1.2 Vollständige Implementation

Erstelle `core/rag/perplexity_portkey_client.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Perplexity + Portkey RAG Client
==========================================

Produktionsreife Implementation für medizinisches RAG.

Autor: MedExamAI Team
Version: 3.0
"""

import json
import os
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import requests

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    """Konfiguriert Logging."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("MedExamAI.RAG")
    logger.setLevel(getattr(logging, level))
    
    # File Handler
    log_file = log_dir / f"rag_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger


# ============================================================================
# KONFIGURATION
# ============================================================================

@dataclass
class PortkeyConfig:
    """Portkey Gateway Konfiguration."""
    api_key: str = field(default_factory=lambda: os.getenv("PORTKEY_API_KEY", ""))
    base_url: str = "https://api.portkey.ai/v1"
    virtual_key_perplexity_1: str = field(default_factory=lambda: os.getenv("PORTKEY_VIRTUAL_KEY_PPX_1", ""))
    virtual_key_perplexity_2: str = field(default_factory=lambda: os.getenv("PORTKEY_VIRTUAL_KEY_PPX_2", ""))
    
    # Fallback: Direkte Perplexity Keys wenn kein Portkey
    perplexity_key_1: str = field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY_1", ""))
    perplexity_key_2: str = field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY_2", ""))
    
    def has_portkey(self) -> bool:
        return bool(self.api_key)
    
    def has_direct_perplexity(self) -> bool:
        return bool(self.perplexity_key_1 or self.perplexity_key_2)


@dataclass
class RAGConfig:
    """RAG System Konfiguration."""
    # Modell
    model: str = "llama-3.1-sonar-large-128k-online"
    temperature: float = 0.1  # Niedrig für Fakten
    max_tokens: int = 2000
    
    # Rate Limiting
    requests_per_minute: int = 20
    min_request_delay: float = 3.0  # Sekunden
    
    # Budget (in USD)
    max_cost_per_session: float = 5.0
    cost_per_1k_tokens: float = 0.001
    
    # Retry
    max_retries: int = 3
    retry_delay: float = 5.0
    retry_backoff: float = 2.0  # Exponential backoff
    
    # Cache
    cache_enabled: bool = True
    cache_dir: Path = field(default_factory=lambda: Path("cache/rag"))
    cache_ttl_hours: int = 168  # 1 Woche
    
    # Logging
    log_dir: Path = field(default_factory=lambda: Path("logs/rag"))
    log_level: str = "INFO"


class QueryType(Enum):
    """Medizinische Query-Typen mit optimierten Templates."""
    DOSIERUNG = "dosierung"
    KLASSIFIKATION = "klassifikation"
    RECHTLICH = "rechtlich"
    DIAGNOSTIK = "diagnostik"
    THERAPIE = "therapie"
    DEFINITION = "definition"
    LEITLINIE = "leitlinie"
    NOTFALL = "notfall"
    VERIFIZIERUNG = "verifizierung"  # Für Gold Standard Check


# ============================================================================
# QUERY TEMPLATES (Medizinisch optimiert für deutsche Prüfung)
# ============================================================================

QUERY_TEMPLATES: Dict[QueryType, str] = {
    QueryType.DOSIERUNG: """
Du bist ein deutscher Facharzt für Innere Medizin. Beantworte PRÄZISE nach aktueller AWMF-Leitlinie.

FRAGE: Exakte Dosierung von {medikament} bei {indikation}?

ANTWORTFORMAT (NUR diese Struktur, keine Einleitung):
```
STANDARDDOSIS:
- Erwachsene: [Dosis] [Frequenz] [Dauer]
- Kinder: [Dosis/kg] oder "nicht zugelassen"

ANPASSUNG:
- Niereninsuffizienz (GFR <30): [Anpassung]
- Leberinsuffizienz: [Anpassung]
- Alter >65: [Anpassung]

KONTRAINDIKATIONEN:
- Absolut: [Liste]
- Relativ: [Liste]

QUELLE: [AWMF-Leitlinie mit Registernummer und Jahr]
```
""",

    QueryType.KLASSIFIKATION: """
Du bist ein deutscher Facharzt. Beantworte PRÄZISE:

FRAGE: Klassifikation(en) für {krankheit}?

ANTWORTFORMAT (NUR diese Struktur):
```
KLASSIFIKATION: [Name, z.B. "NYHA", "Garden", "CHA2DS2-VASc"]
AUTOR/ORGANISATION: [Wer hat sie entwickelt]

STADIEN/GRADE:
- Stadium/Grad I: [Kriterien]
- Stadium/Grad II: [Kriterien]
- Stadium/Grad III: [Kriterien]
- Stadium/Grad IV: [Kriterien] (falls vorhanden)

KLINISCHE KONSEQUENZ:
- Stadium I-II: [Therapie]
- Stadium III-IV: [Therapie]

QUELLE: [Leitlinie/Originalpublikation]
```
""",

    QueryType.RECHTLICH: """
Du bist ein deutscher Medizinrechtler. Beantworte PRÄZISE:

FRAGE: Rechtliche Aspekte bei {kontext}?

ANTWORTFORMAT (NUR diese Struktur):
```
RELEVANTE PARAGRAPHEN:
- §630d BGB: [Einwilligung - Kerninhalte]
- §630e BGB: [Aufklärung - Kerninhalte]
- §630f BGB: [Dokumentation - Kerninhalte]
- Weitere: [falls relevant]

AUFKLÄRUNGSPFLICHT für {kontext}:
- Zeitpunkt: [wann]
- Inhalt: [was muss aufgeklärt werden]
- Form: [mündlich/schriftlich]

DOKUMENTATIONSPFLICHT:
- Pflichtinhalte: [Liste]
- Aufbewahrungsfrist: [Jahre]

BESONDERHEITEN:
- Notfall: [Regelung]
- Minderjährige: [Regelung]
- Nicht einwilligungsfähig: [Regelung]
```
""",

    QueryType.VERIFIZIERUNG: """
Du bist ein deutscher Prüfer für die Kenntnisprüfung. Verifiziere die folgende Antwort.

FRAGE: {frage}
GEGEBENE ANTWORT: {antwort}

PRÜFE auf:
1. Sachliche Korrektheit (stimmen die Fakten?)
2. Vollständigkeit (fehlt etwas Wichtiges?)
3. Dosierungen (korrekt nach aktueller Leitlinie?)
4. Klassifikationen (mit korrekten Namen?)
5. Rechtliche Aspekte (§630 BGB korrekt?)

ANTWORTFORMAT:
```
KORREKTHEIT: [KORREKT / TEILWEISE KORREKT / FALSCH]

FEHLER (falls vorhanden):
- [Fehler 1]: [Korrektur]
- [Fehler 2]: [Korrektur]

FEHLENDE INFORMATIONEN:
- [Was fehlt 1]
- [Was fehlt 2]

KORRIGIERTE ANTWORT (falls nötig):
[Vollständige korrigierte Antwort]

KONFIDENZ: [1-10]
QUELLE: [Leitlinie]
```
""",

    QueryType.NOTFALL: """
Du bist Notarzt. Beantworte nach aktuellem ERC/DGAI-Standard:

FRAGE: Notfallmanagement bei {notfall}?

ANTWORTFORMAT (ABCDE-Schema):
```
A - AIRWAY:
- Sofortmaßnahme: [Aktion]
- Material: [benötigt]
- Eskalation: [wann Intubation]

B - BREATHING:
- Ziel-SpO2: [%]
- O2-Gabe: [L/min, Maske]
- Eskalation: [wann Beatmung]

C - CIRCULATION:
- Sofortmaßnahme: [Aktion]
- Zugänge: [Anzahl, Größe]
- Volumen: [ml, Art]
- Medikamente: [mit EXAKTER Dosis]

D - DISABILITY:
- GCS-Dokumentation
- Pupillen
- BZ-Messung
- Eskalation: [wann CCT]

E - EXPOSURE:
- Temperatur
- Ganzkörperinspektion
- Wärmeerhalt

MEDIKAMENTE MIT DOSIS:
- [Medikament 1]: [Dosis] [Applikation]
- [Medikament 2]: [Dosis] [Applikation]
```
"""
}


# ============================================================================
# CACHE SYSTEM
# ============================================================================

class RAGCache:
    """Persistenter Cache für RAG-Antworten."""
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 168):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_file = cache_dir / "rag_cache.json"
        self.cache = self._load()
    
    def _load(self) -> Dict:
        """Lädt Cache von Disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save(self):
        """Speichert Cache auf Disk."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _hash(self, query: str) -> str:
        """Generiert Cache-Key."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    def get(self, query: str) -> Optional[str]:
        """Holt Antwort aus Cache wenn vorhanden und nicht expired."""
        key = self._hash(query)
        if key in self.cache:
            entry = self.cache[key]
            cached_time = datetime.fromisoformat(entry['timestamp'])
            if datetime.now() - cached_time < self.ttl:
                return entry['response']
            else:
                # Expired
                del self.cache[key]
                self._save()
        return None
    
    def set(self, query: str, response: str):
        """Speichert Antwort im Cache."""
        key = self._hash(query)
        self.cache[key] = {
            'query': query[:200],  # Gekürzt für Übersicht
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        self._save()
    
    def stats(self) -> Dict:
        """Cache-Statistiken."""
        return {
            'total_entries': len(self.cache),
            'cache_file': str(self.cache_file),
            'ttl_hours': self.ttl.total_seconds() / 3600
        }


# ============================================================================
# BUDGET TRACKER
# ============================================================================

class BudgetTracker:
    """Verfolgt API-Kosten."""
    
    def __init__(self, max_budget: float, cost_per_1k_tokens: float):
        self.max_budget = max_budget
        self.cost_per_1k = cost_per_1k_tokens
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
    
    def add_usage(self, input_tokens: int, output_tokens: int):
        """Fügt Token-Nutzung hinzu."""
        total_tokens = input_tokens + output_tokens
        cost = (total_tokens / 1000) * self.cost_per_1k
        
        self.total_tokens += total_tokens
        self.total_cost += cost
        self.request_count += 1
    
    def can_continue(self) -> bool:
        """Prüft ob Budget noch vorhanden."""
        return self.total_cost < self.max_budget
    
    def remaining(self) -> float:
        """Verbleibendes Budget."""
        return max(0, self.max_budget - self.total_cost)
    
    def stats(self) -> Dict:
        """Budget-Statistiken."""
        return {
            'total_cost_usd': round(self.total_cost, 4),
            'remaining_usd': round(self.remaining(), 4),
            'total_tokens': self.total_tokens,
            'request_count': self.request_count,
            'avg_tokens_per_request': self.total_tokens // max(1, self.request_count)
        }


# ============================================================================
# PERPLEXITY + PORTKEY CLIENT
# ============================================================================

class PerplexityPortkeyClient:
    """
    Produktionsreifer Client für Perplexity via Portkey Gateway.
    
    Features:
    - Automatisches Failover zwischen 2 API Keys
    - Response Caching
    - Budget Tracking
    - Rate Limiting
    - Comprehensive Logging
    - Retry mit Exponential Backoff
    """
    
    def __init__(
        self,
        portkey_config: Optional[PortkeyConfig] = None,
        rag_config: Optional[RAGConfig] = None
    ):
        self.portkey = portkey_config or PortkeyConfig()
        self.config = rag_config or RAGConfig()
        
        # Setup
        self.logger = setup_logging(self.config.log_dir, self.config.log_level)
        self.cache = RAGCache(self.config.cache_dir, self.config.cache_ttl_hours) if self.config.cache_enabled else None
        self.budget = BudgetTracker(self.config.max_cost_per_session, self.config.cost_per_1k_tokens)
        
        # State
        self.current_key_index = 0
        self.last_request_time = 0.0
        self.session_start = datetime.now()
        
        # API Keys (Portkey Virtual Keys oder direkte Perplexity Keys)
        self.api_keys = self._setup_api_keys()
        
        self.logger.info(f"🚀 PerplexityPortkeyClient initialisiert")
        self.logger.info(f"   Mode: {'Portkey Gateway' if self.portkey.has_portkey() else 'Direct Perplexity'}")
        self.logger.info(f"   API Keys: {len(self.api_keys)} verfügbar")
        self.logger.info(f"   Cache: {'Aktiviert' if self.cache else 'Deaktiviert'}")
        self.logger.info(f"   Budget: ${self.config.max_cost_per_session}")
    
    def _setup_api_keys(self) -> List[Tuple[str, str]]:
        """Richtet API Keys ein. Returns: [(key, base_url), ...]"""
        keys = []
        
        if self.portkey.has_portkey():
            # Portkey Mode: Verwende Virtual Keys
            if self.portkey.virtual_key_perplexity_1:
                keys.append((self.portkey.virtual_key_perplexity_1, self.portkey.base_url))
            if self.portkey.virtual_key_perplexity_2:
                keys.append((self.portkey.virtual_key_perplexity_2, self.portkey.base_url))
        
        if not keys and self.portkey.has_direct_perplexity():
            # Direct Perplexity Mode
            perplexity_url = "https://api.perplexity.ai/chat/completions"
            if self.portkey.perplexity_key_1:
                keys.append((self.portkey.perplexity_key_1, perplexity_url))
            if self.portkey.perplexity_key_2:
                keys.append((self.portkey.perplexity_key_2, perplexity_url))
        
        if not keys:
            self.logger.warning("⚠️ Keine API Keys konfiguriert!")
        
        return keys
    
    def _get_next_key(self) -> Optional[Tuple[str, str]]:
        """Rotiert durch API Keys."""
        if not self.api_keys:
            return None
        
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _rate_limit(self):
        """Enforces Rate Limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.min_request_delay:
            sleep_time = self.config.min_request_delay - elapsed
            self.logger.debug(f"⏳ Rate limit: {sleep_time:.1f}s warten")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, prompt: str, api_key: str, base_url: str) -> Optional[Dict]:
        """Macht einzelnen API Request."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Portkey-spezifische Header
        if self.portkey.has_portkey() and "portkey" in base_url:
            headers["x-portkey-api-key"] = self.portkey.api_key
            headers["x-portkey-provider"] = "perplexity"
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist ein präziser deutscher Medizinexperte für die Kenntnisprüfung. "
                               "Antworte IMMER im angeforderten Format. Keine Einleitungen oder Floskeln."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        try:
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.warning("⏱️ Request Timeout")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"❌ HTTP Error: {e.response.status_code}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Request Error: {e}")
            return None
    
    def query(
        self,
        query_type: QueryType,
        use_cache: bool = True,
        **kwargs
    ) -> Optional[str]:
        """
        Führt medizinische Query aus.
        
        Args:
            query_type: Art der Query (DOSIERUNG, KLASSIFIKATION, etc.)
            use_cache: Cache verwenden?
            **kwargs: Parameter für das Template
        
        Returns:
            Antwort als String oder None bei Fehler
        """
        # Budget prüfen
        if not self.budget.can_continue():
            self.logger.error(f"🚫 Budget erschöpft! Verbraucht: ${self.budget.total_cost:.4f}")
            return None
        
        # Template füllen
        template = QUERY_TEMPLATES.get(query_type)
        if not template:
            self.logger.error(f"❌ Unbekannter QueryType: {query_type}")
            return None
        
        try:
            prompt = template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"❌ Fehlender Parameter im Template: {e}")
            return None
        
        # Cache prüfen
        if use_cache and self.cache:
            cached = self.cache.get(prompt)
            if cached:
                self.logger.info(f"💾 Cache Hit für {query_type.value}")
                return cached
        
        # Rate Limiting
        self._rate_limit()
        
        # Request mit Retry
        for attempt in range(self.config.max_retries):
            key_info = self._get_next_key()
            if not key_info:
                self.logger.error("❌ Keine API Keys verfügbar")
                return None
            
            api_key, base_url = key_info
            self.logger.info(f"🌐 Query {query_type.value} (Versuch {attempt + 1}/{self.config.max_retries})")
            
            result = self._make_request(prompt, api_key, base_url)
            
            if result and 'choices' in result:
                response_text = result['choices'][0]['message']['content']
                
                # Usage tracking
                usage = result.get('usage', {})
                self.budget.add_usage(
                    usage.get('prompt_tokens', 500),
                    usage.get('completion_tokens', 500)
                )
                
                # Cache speichern
                if self.cache:
                    self.cache.set(prompt, response_text)
                
                self.logger.info(f"✅ Query erfolgreich ({self.budget.stats()['total_cost_usd']:.4f} USD)")
                return response_text
            
            # Retry mit Backoff
            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (self.config.retry_backoff ** attempt)
                self.logger.warning(f"⏳ Retry in {delay:.1f}s...")
                time.sleep(delay)
        
        self.logger.error(f"❌ Query fehlgeschlagen nach {self.config.max_retries} Versuchen")
        return None
    
    def query_dosierung(self, medikament: str, indikation: str) -> Optional[str]:
        """Shortcut für Dosierungs-Query."""
        return self.query(QueryType.DOSIERUNG, medikament=medikament, indikation=indikation)
    
    def query_klassifikation(self, krankheit: str) -> Optional[str]:
        """Shortcut für Klassifikations-Query."""
        return self.query(QueryType.KLASSIFIKATION, krankheit=krankheit)
    
    def query_rechtlich(self, kontext: str) -> Optional[str]:
        """Shortcut für Rechtliche Query."""
        return self.query(QueryType.RECHTLICH, kontext=kontext)
    
    def query_notfall(self, notfall: str) -> Optional[str]:
        """Shortcut für Notfall-Query."""
        return self.query(QueryType.NOTFALL, notfall=notfall)
    
    def verify_answer(self, frage: str, antwort: str) -> Optional[str]:
        """Verifiziert eine Antwort gegen aktuelle Leitlinien."""
        return self.query(QueryType.VERIFIZIERUNG, frage=frage, antwort=antwort)
    
    def stats(self) -> Dict:
        """Gibt Session-Statistiken zurück."""
        return {
            'session_start': self.session_start.isoformat(),
            'session_duration_min': (datetime.now() - self.session_start).total_seconds() / 60,
            'budget': self.budget.stats(),
            'cache': self.cache.stats() if self.cache else None,
            'api_keys_available': len(self.api_keys)
        }
    
    def print_stats(self):
        """Zeigt Session-Statistiken."""
        stats = self.stats()
        print("\n" + "="*60)
        print("📊 RAG SESSION STATISTIK")
        print("="*60)
        print(f"⏱️  Dauer: {stats['session_duration_min']:.1f} Minuten")
        print(f"💰 Kosten: ${stats['budget']['total_cost_usd']:.4f} / ${self.config.max_cost_per_session}")
        print(f"📝 Requests: {stats['budget']['request_count']}")
        print(f"🔤 Tokens: {stats['budget']['total_tokens']}")
        if stats['cache']:
            print(f"💾 Cache: {stats['cache']['total_entries']} Einträge")
        print("="*60)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_rag_client(
    portkey_api_key: Optional[str] = None,
    perplexity_key_1: Optional[str] = None,
    perplexity_key_2: Optional[str] = None,
    max_budget: float = 5.0
) -> PerplexityPortkeyClient:
    """Factory-Funktion für einfache Client-Erstellung."""
    
    portkey_config = PortkeyConfig(
        api_key=portkey_api_key or os.getenv("PORTKEY_API_KEY", ""),
        perplexity_key_1=perplexity_key_1 or os.getenv("PERPLEXITY_API_KEY_1", ""),
        perplexity_key_2=perplexity_key_2 or os.getenv("PERPLEXITY_API_KEY_2", "")
    )
    
    rag_config = RAGConfig(max_cost_per_session=max_budget)
    
    return PerplexityPortkeyClient(portkey_config, rag_config)


# ============================================================================
# CLI / TEST
# ============================================================================

if __name__ == "__main__":
    print("🧪 Teste Perplexity+Portkey RAG Client...")
    
    client = create_rag_client(max_budget=1.0)
    
    # Test 1: Dosierung
    print("\n📋 Test 1: Dosierung")
    result = client.query_dosierung("Amoxicillin", "ambulant erworbene Pneumonie")
    if result:
        print(result[:500])
    
    # Test 2: Klassifikation
    print("\n📋 Test 2: Klassifikation")
    result = client.query_klassifikation("Herzinsuffizienz")
    if result:
        print(result[:500])
    
    # Statistiken
    client.print_stats()
```

---

# 🏆 TEIL 2: GOLD STANDARD VALIDIERUNG

## 2.1 Konzept

Der `_GOLD_STANDARD/` Ordner enthält **echte Prüfungsprotokolle** - das ist die absolute Wahrheitsquelle.

```
_GOLD_STANDARD/
├── Protokoll_2024_01.pdf      # Echte Prüfungsfragen
├── Protokoll_2024_02.pdf
├── Protokoll_2023_*.pdf
├── Erfahrungsberichte/
│   ├── Teilnehmer_A.docx
│   └── Teilnehmer_B.docx
└── Themenlisten/
    └── Häufige_Themen.xlsx
```

## 2.2 Gold Standard Comparator

Erstelle `core/validation/gold_standard_comparator.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Gold Standard Comparator
===================================

Vergleicht generierte Q&A mit echten Prüfungsprotokollen.

Funktionen:
1. Themen-Matching: Welche Gold Standard Themen sind abgedeckt?
2. Antwort-Verifizierung: Stimmen unsere Antworten mit den echten?
3. Lücken-Analyse: Was fehlt in unseren Q&A?
4. Präzisions-Score: Wie gut sind wir?
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from difflib import SequenceMatcher
import logging

# ============================================================================
# DATENSTRUKTUREN
# ============================================================================

@dataclass
class GoldStandardEntry:
    """Ein Eintrag aus dem Gold Standard."""
    id: str
    frage: str
    erwartete_antwort: str
    thema: str
    kategorie: str
    quelle: str  # z.B. "Protokoll_2024_01.pdf"
    schwierigkeit: str = "mittel"
    tags: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Ergebnis eines Vergleichs."""
    gold_id: str
    generated_id: Optional[str]
    match_score: float  # 0.0 - 1.0
    status: str  # "MATCH", "PARTIAL", "MISSING", "DIFFERENT"
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Gesamtbericht der Validierung."""
    total_gold_standard: int
    total_generated: int
    matches: int
    partial_matches: int
    missing: int
    different: int
    coverage_percent: float
    precision_score: float
    missing_topics: List[str]
    recommendations: List[str]


# ============================================================================
# GOLD STANDARD LOADER
# ============================================================================

class GoldStandardLoader:
    """Lädt und parst Gold Standard Dokumente."""
    
    def __init__(self, gold_standard_dir: str):
        self.gold_dir = Path(gold_standard_dir)
        self.logger = logging.getLogger("MedExamAI.GoldStandard")
        
        if not self.gold_dir.exists():
            raise ValueError(f"Gold Standard Verzeichnis nicht gefunden: {gold_standard_dir}")
    
    def load_all(self) -> List[GoldStandardEntry]:
        """Lädt alle Gold Standard Einträge."""
        entries = []
        
        # JSON-Dateien (bereits extrahiert)
        for json_file in self.gold_dir.rglob("*.json"):
            entries.extend(self._load_json(json_file))
        
        # Falls keine JSON vorhanden, versuche PDFs zu finden
        if not entries:
            self.logger.warning("Keine JSON Gold Standard Dateien gefunden.")
            self.logger.info("Bitte extrahiere zuerst die PDFs mit dem Extraction-Script.")
            
            # Zeige vorhandene Dateien
            pdf_count = len(list(self.gold_dir.rglob("*.pdf")))
            docx_count = len(list(self.gold_dir.rglob("*.docx")))
            self.logger.info(f"Gefunden: {pdf_count} PDFs, {docx_count} DOCX-Dateien")
        
        self.logger.info(f"✅ {len(entries)} Gold Standard Einträge geladen")
        return entries
    
    def _load_json(self, filepath: Path) -> List[GoldStandardEntry]:
        """Lädt Einträge aus JSON-Datei."""
        entries = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle verschiedene Strukturen
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and 'questions' in data:
                items = data['questions']
            elif isinstance(data, dict) and 'qa_pairs' in data:
                items = data['qa_pairs']
            else:
                items = [data]
            
            for i, item in enumerate(items):
                entry = GoldStandardEntry(
                    id=item.get('id', f"{filepath.stem}_{i}"),
                    frage=item.get('frage', item.get('question', '')),
                    erwartete_antwort=item.get('antwort', item.get('answer', item.get('erwartete_antwort', ''))),
                    thema=item.get('thema', item.get('topic', 'Unbekannt')),
                    kategorie=item.get('kategorie', item.get('category', 'Allgemein')),
                    quelle=str(filepath.name),
                    tags=item.get('tags', [])
                )
                entries.append(entry)
                
        except Exception as e:
            self.logger.error(f"Fehler beim Laden von {filepath}: {e}")
        
        return entries


# ============================================================================
# COMPARATOR ENGINE
# ============================================================================

class GoldStandardComparator:
    """
    Vergleicht generierte Q&A mit Gold Standard.
    
    Matching-Strategien:
    1. Exaktes Themen-Matching
    2. Semantische Ähnlichkeit (Frage-zu-Frage)
    3. Keyword-Overlap
    4. Antwort-Verifikation
    """
    
    def __init__(
        self,
        gold_standard_dir: str,
        similarity_threshold: float = 0.6
    ):
        self.loader = GoldStandardLoader(gold_standard_dir)
        self.gold_entries = self.loader.load_all()
        self.threshold = similarity_threshold
        self.logger = logging.getLogger("MedExamAI.Comparator")
        
        # Index für schnelles Matching
        self._build_index()
    
    def _build_index(self):
        """Baut Such-Index für Gold Standard."""
        self.thema_index = defaultdict(list)
        self.keyword_index = defaultdict(list)
        
        for entry in self.gold_entries:
            # Thema-Index
            thema_normalized = self._normalize(entry.thema)
            self.thema_index[thema_normalized].append(entry)
            
            # Keyword-Index
            keywords = self._extract_keywords(entry.frage)
            for kw in keywords:
                self.keyword_index[kw].append(entry)
    
    def _normalize(self, text: str) -> str:
        """Normalisiert Text für Matching."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extrahiert medizinische Keywords."""
        # Stopwords (deutsch)
        stopwords = {
            'der', 'die', 'das', 'und', 'oder', 'bei', 'mit', 'von', 'zu',
            'ist', 'sind', 'ein', 'eine', 'einer', 'einem', 'den', 'dem',
            'was', 'wie', 'welche', 'welcher', 'welches', 'kann', 'können'
        }
        
        words = self._normalize(text).split()
        keywords = {w for w in words if len(w) > 3 and w not in stopwords}
        return keywords
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Berechnet Ähnlichkeit zwischen zwei Texten."""
        return SequenceMatcher(None, self._normalize(text1), self._normalize(text2)).ratio()
    
    def _keyword_overlap(self, text1: str, text2: str) -> float:
        """Berechnet Keyword-Overlap."""
        kw1 = self._extract_keywords(text1)
        kw2 = self._extract_keywords(text2)
        
        if not kw1 or not kw2:
            return 0.0
        
        intersection = kw1 & kw2
        union = kw1 | kw2
        
        return len(intersection) / len(union)
    
    def find_best_match(self, generated_qa: Dict) -> Tuple[Optional[GoldStandardEntry], float]:
        """
        Findet besten Match im Gold Standard für eine generierte Frage.
        
        Returns:
            (GoldStandardEntry oder None, Similarity Score)
        """
        gen_frage = generated_qa.get('frage', generated_qa.get('question', ''))
        
        best_match = None
        best_score = 0.0
        
        # Strategie 1: Keyword-basierte Vorfilterung
        gen_keywords = self._extract_keywords(gen_frage)
        candidates = set()
        
        for kw in gen_keywords:
            if kw in self.keyword_index:
                candidates.update(self.keyword_index[kw])
        
        # Falls keine Kandidaten, alle prüfen
        if not candidates:
            candidates = self.gold_entries
        
        # Strategie 2: Detailliertes Scoring
        for gold_entry in candidates:
            # Kombinierter Score
            text_sim = self._similarity(gen_frage, gold_entry.frage)
            kw_overlap = self._keyword_overlap(gen_frage, gold_entry.frage)
            
            # Gewichteter Score
            score = 0.6 * text_sim + 0.4 * kw_overlap
            
            if score > best_score:
                best_score = score
                best_match = gold_entry
        
        return best_match, best_score
    
    def compare_single(self, generated_qa: Dict) -> ComparisonResult:
        """Vergleicht einzelne generierte Frage mit Gold Standard."""
        gen_id = generated_qa.get('id', 'unknown')
        gen_frage = generated_qa.get('frage', generated_qa.get('question', ''))
        gen_antwort = generated_qa.get('antwort', generated_qa.get('answer', ''))
        
        # Finde besten Match
        gold_match, match_score = self.find_best_match(generated_qa)
        
        if gold_match is None:
            return ComparisonResult(
                gold_id="NONE",
                generated_id=gen_id,
                match_score=0.0,
                status="MISSING",
                details={"reason": "Kein Match im Gold Standard gefunden"}
            )
        
        # Bestimme Status basierend auf Score
        if match_score >= 0.8:
            status = "MATCH"
        elif match_score >= self.threshold:
            status = "PARTIAL"
        else:
            status = "DIFFERENT"
        
        # Antwort-Vergleich wenn Match
        answer_similarity = 0.0
        if status in ["MATCH", "PARTIAL"]:
            # Vereinfachter Antwort-Vergleich
            if isinstance(gen_antwort, dict):
                # Strukturierte Antwort - vergleiche Therapie-Abschnitt
                gen_text = str(gen_antwort.get('4_therapie', ''))
            else:
                gen_text = str(gen_antwort)
            
            answer_similarity = self._keyword_overlap(gen_text, gold_match.erwartete_antwort)
        
        return ComparisonResult(
            gold_id=gold_match.id,
            generated_id=gen_id,
            match_score=match_score,
            status=status,
            details={
                "gold_frage": gold_match.frage[:100],
                "gold_thema": gold_match.thema,
                "answer_similarity": answer_similarity,
                "gold_quelle": gold_match.quelle
            }
        )
    
    def compare_all(self, generated_qa_list: List[Dict]) -> ValidationReport:
        """
        Vergleicht alle generierten Q&A mit Gold Standard.
        
        Returns:
            ValidationReport mit Statistiken und Empfehlungen
        """
        self.logger.info(f"🔍 Starte Vergleich: {len(generated_qa_list)} generierte vs {len(self.gold_entries)} Gold Standard")
        
        results = []
        status_counts = defaultdict(int)
        matched_gold_ids = set()
        
        for gen_qa in generated_qa_list:
            result = self.compare_single(gen_qa)
            results.append(result)
            status_counts[result.status] += 1
            
            if result.status in ["MATCH", "PARTIAL"]:
                matched_gold_ids.add(result.gold_id)
        
        # Finde fehlende Gold Standard Themen
        all_gold_ids = {e.id for e in self.gold_entries}
        missing_gold_ids = all_gold_ids - matched_gold_ids
        missing_topics = [
            e.thema for e in self.gold_entries 
            if e.id in missing_gold_ids
        ]
        
        # Berechne Metriken
        coverage = len(matched_gold_ids) / len(self.gold_entries) * 100 if self.gold_entries else 0
        
        # Präzision: Durchschnittlicher Match-Score der Matches
        match_scores = [r.match_score for r in results if r.status in ["MATCH", "PARTIAL"]]
        precision = sum(match_scores) / len(match_scores) * 100 if match_scores else 0
        
        # Empfehlungen generieren
        recommendations = []
        
        if coverage < 80:
            recommendations.append(f"⚠️ Coverage nur {coverage:.1f}% - Füge mehr Fragen zu fehlenden Themen hinzu")
        
        if precision < 70:
            recommendations.append(f"⚠️ Präzision nur {precision:.1f}% - Überprüfe Antwortqualität")
        
        if status_counts["DIFFERENT"] > len(generated_qa_list) * 0.2:
            recommendations.append("⚠️ >20% der Fragen weichen stark ab - Manuelle Prüfung empfohlen")
        
        if len(missing_topics) > 10:
            top_missing = list(set(missing_topics))[:10]
            recommendations.append(f"📝 Fehlende Themen: {', '.join(top_missing)}")
        
        report = ValidationReport(
            total_gold_standard=len(self.gold_entries),
            total_generated=len(generated_qa_list),
            matches=status_counts["MATCH"],
            partial_matches=status_counts["PARTIAL"],
            missing=status_counts["MISSING"],
            different=status_counts["DIFFERENT"],
            coverage_percent=round(coverage, 2),
            precision_score=round(precision, 2),
            missing_topics=list(set(missing_topics)),
            recommendations=recommendations
        )
        
        return report
    
    def print_report(self, report: ValidationReport):
        """Gibt Validierungsbericht aus."""
        print("\n" + "="*70)
        print("🏆 GOLD STANDARD VALIDIERUNGSBERICHT")
        print("="*70)
        
        print(f"\n📊 ÜBERSICHT:")
        print(f"   Gold Standard Einträge: {report.total_gold_standard}")
        print(f"   Generierte Q&A:         {report.total_generated}")
        
        print(f"\n📈 MATCHING:")
        print(f"   ✅ Vollständige Matches: {report.matches}")
        print(f"   🔶 Teilweise Matches:    {report.partial_matches}")
        print(f"   ❌ Abweichend:           {report.different}")
        print(f"   ⚪ Kein Match:           {report.missing}")
        
        print(f"\n📐 METRIKEN:")
        print(f"   Coverage:  {report.coverage_percent}%")
        print(f"   Präzision: {report.precision_score}%")
        
        # Coverage-Visualisierung
        coverage_bar = "█" * int(report.coverage_percent / 5) + "░" * (20 - int(report.coverage_percent / 5))
        print(f"   [{coverage_bar}] {report.coverage_percent}%")
        
        if report.recommendations:
            print(f"\n💡 EMPFEHLUNGEN:")
            for rec in report.recommendations:
                print(f"   {rec}")
        
        if report.missing_topics and len(report.missing_topics) <= 20:
            print(f"\n📝 FEHLENDE THEMEN ({len(report.missing_topics)}):")
            for topic in report.missing_topics[:20]:
                print(f"   • {topic}")
        
        print("\n" + "="*70)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Gold Standard Validierung')
    parser.add_argument('--gold', '-g', required=True, help='Pfad zum _GOLD_STANDARD Ordner')
    parser.add_argument('--generated', '-i', required=True, help='Pfad zur generierten Q&A JSON')
    parser.add_argument('--output', '-o', default='validation_report.json', help='Output Report')
    parser.add_argument('--threshold', '-t', type=float, default=0.6, help='Similarity Threshold')
    
    args = parser.parse_args()
    
    # Laden
    with open(args.generated, 'r', encoding='utf-8') as f:
        generated = json.load(f)
    
    if isinstance(generated, dict) and 'qa_pairs' in generated:
        generated = generated['qa_pairs']
    
    print(f"📥 {len(generated)} generierte Q&A geladen")
    
    # Vergleichen
    comparator = GoldStandardComparator(args.gold, args.threshold)
    report = comparator.compare_all(generated)
    
    # Ausgabe
    comparator.print_report(report)
    
    # Speichern
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'coverage_percent': report.coverage_percent,
                'precision_score': report.precision_score,
                'total_gold': report.total_gold_standard,
                'total_generated': report.total_generated
            },
            'missing_topics': report.missing_topics,
            'recommendations': report.recommendations
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Report gespeichert: {args.output}")
```

---

# 🛡️ TEIL 3: MEDICAL VALIDATION LAYER (4 Prüfer)

## 3.1 Die 4 Prüfer

Erstelle `core/validation/medical_validators.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Medical Validation Layer
====================================

4 Prüfer für medizinische Qualitätssicherung:
1. 💊 Dosage Validator - Prüft Medikamentendosierungen
2. 📋 ICD-10 Validator - Prüft Diagnose-Codes
3. 🧪 Lab Value Validator - Prüft Laborwerte
4. 🧠 Logical Consistency - Prüft Widersprüche
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging


class ValidationSeverity(Enum):
    """Schweregrad einer Validierungswarnung."""
    INFO = "info"           # Hinweis
    WARNING = "warning"     # Warnung
    ERROR = "error"         # Fehler
    CRITICAL = "critical"   # Kritisch (blockiert)


@dataclass
class ValidationIssue:
    """Ein Validierungsproblem."""
    validator: str
    severity: ValidationSeverity
    message: str
    field: str
    value: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Ergebnis der Validierung."""
    qa_id: str
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    quarantine: bool = False
    
    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.CRITICAL:
            self.is_valid = False
            self.quarantine = True
        elif issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False


# ============================================================================
# 1. DOSAGE VALIDATOR 💊
# ============================================================================

class DosageValidator:
    """
    Prüft Medikamentendosierungen auf Plausibilität.
    
    Erkennt:
    - Überdosierungen (tödlich)
    - Unterdosierungen (unwirksam)
    - Falsche Einheiten
    - Fehlende Frequenzangaben
    """
    
    # Referenzdatenbank: Medikament -> (min_dose_mg, max_dose_mg_pro_tag, einheit)
    DOSAGE_LIMITS = {
        # Analgetika
        "paracetamol": (500, 4000, "mg"),
        "ibuprofen": (200, 2400, "mg"),
        "metamizol": (500, 4000, "mg"),
        "morphin": (5, 200, "mg"),
        
        # Kardiovaskulär
        "metoprolol": (25, 200, "mg"),
        "ramipril": (1.25, 10, "mg"),
        "amlodipin": (2.5, 10, "mg"),
        "furosemid": (20, 250, "mg"),
        
        # Antibiotika
        "amoxicillin": (500, 3000, "mg"),
        "ciprofloxacin": (250, 1500, "mg"),
        "azithromycin": (250, 500, "mg"),
        "meropenem": (500, 6000, "mg"),
        
        # Psychiatrie
        "sertralin": (25, 200, "mg"),
        "mirtazapin": (15, 45, "mg"),
        "risperidon": (0.5, 16, "mg"),
        "methylphenidat": (5, 80, "mg"),  # WICHTIG: Max 80mg!
        
        # Antikoagulation
        "heparin": (5000, 35000, "IE"),
        "enoxaparin": (20, 150, "mg"),
        "rivaroxaban": (10, 20, "mg"),
        
        # Schilddrüse
        "l-thyroxin": (25, 300, "µg"),
        
        # Diabetes
        "metformin": (500, 3000, "mg"),
        "insulin": (1, 200, "IE"),
    }
    
    def __init__(self):
        self.logger = logging.getLogger("MedExamAI.DosageValidator")
    
    def _extract_dosages(self, text: str) -> List[Dict]:
        """Extrahiert Dosierungsangaben aus Text."""
        dosages = []
        
        # Pattern: Medikament + Dosis
        patterns = [
            # "Amoxicillin 1000mg" oder "Amoxicillin 1g"
            r'(\w+)\s+(\d+(?:[.,]\d+)?)\s*(mg|g|µg|mcg|IE|IU|ml)',
            # "1000mg Amoxicillin"
            r'(\d+(?:[.,]\d+)?)\s*(mg|g|µg|mcg|IE|IU)\s+(\w+)',
            # "3x1g Amoxicillin" oder "Amoxicillin 3x1g"
            r'(\w+)\s+(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(mg|g)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                dosages.append({
                    'raw': match,
                    'text': ' '.join(match)
                })
        
        return dosages
    
    def _normalize_dose(self, value: float, unit: str) -> Tuple[float, str]:
        """Normalisiert Dosis zu mg."""
        unit = unit.lower()
        
        if unit == 'g':
            return value * 1000, 'mg'
        elif unit in ['µg', 'mcg']:
            return value / 1000, 'mg'
        elif unit in ['ie', 'iu']:
            return value, 'IE'
        else:
            return value, unit
    
    def validate(self, qa: Dict) -> List[ValidationIssue]:
        """Validiert Dosierungen in einer Q&A."""
        issues = []
        
        # Extrahiere Text aus Antwort
        antwort = qa.get('antwort', qa.get('answer', ''))
        if isinstance(antwort, dict):
            text = str(antwort.get('4_therapie', ''))
        else:
            text = str(antwort)
        
        # Suche nach bekannten Medikamenten
        text_lower = text.lower()
        
        for med_name, (min_dose, max_dose, expected_unit) in self.DOSAGE_LIMITS.items():
            if med_name in text_lower:
                # Extrahiere Dosis für dieses Medikament
                pattern = rf'{med_name}\s+(\d+(?:[.,]\d+)?)\s*(mg|g|µg|mcg|IE|IU)'
                match = re.search(pattern, text, re.IGNORECASE)
                
                if match:
                    dose_value = float(match.group(1).replace(',', '.'))
                    dose_unit = match.group(2)
                    
                    # Normalisieren
                    normalized_dose, norm_unit = self._normalize_dose(dose_value, dose_unit)
                    
                    # Prüfen
                    if norm_unit == expected_unit or (norm_unit == 'mg' and expected_unit == 'mg'):
                        if normalized_dose > max_dose:
                            severity = ValidationSeverity.CRITICAL if normalized_dose > max_dose * 2 else ValidationSeverity.ERROR
                            issues.append(ValidationIssue(
                                validator="DosageValidator",
                                severity=severity,
                                message=f"ÜBERDOSIERUNG: {med_name.capitalize()} {dose_value}{dose_unit} überschreitet Max ({max_dose}{expected_unit}/Tag)",
                                field="antwort.4_therapie",
                                value=f"{dose_value}{dose_unit}",
                                suggestion=f"Maximaldosis: {max_dose}{expected_unit}/Tag"
                            ))
                        elif normalized_dose < min_dose:
                            issues.append(ValidationIssue(
                                validator="DosageValidator",
                                severity=ValidationSeverity.WARNING,
                                message=f"UNTERDOSIERUNG: {med_name.capitalize()} {dose_value}{dose_unit} unter Mindestdosis ({min_dose}{expected_unit})",
                                field="antwort.4_therapie",
                                value=f"{dose_value}{dose_unit}",
                                suggestion=f"Empfohlene Startdosis: {min_dose}{expected_unit}"
                            ))
        
        return issues


# ============================================================================
# 2. ICD-10 VALIDATOR 📋
# ============================================================================

class ICD10Validator:
    """
    Prüft ICD-10 Codes auf Korrektheit und Konsistenz.
    
    Erkennt:
    - Ungültige ICD-10 Codes
    - Geschlechts-Inkonsistenzen (z.B. C61 bei Frau)
    - Alters-Inkonsistenzen
    """
    
    # Geschlechtsspezifische Codes
    MALE_ONLY_CODES = {
        'C61': 'Prostatakrebs',
        'N40': 'Prostatahyperplasie',
        'N41': 'Prostatitis',
        'N42': 'Sonstige Prostatakrankheiten',
    }
    
    FEMALE_ONLY_CODES = {
        'C50': 'Brustkrebs',  # Kann auch Männer, aber selten
        'C51': 'Vulvakarzinom',
        'C52': 'Vaginalkarzinom',
        'C53': 'Zervixkarzinom',
        'C54': 'Uteruskarzinom',
        'C55': 'Uterus-Krebs',
        'C56': 'Ovarialkarzinom',
        'O': 'Schwangerschaft (alle O-Codes)',
    }
    
    def __init__(self):
        self.logger = logging.getLogger("MedExamAI.ICD10Validator")
    
    def _extract_icd_codes(self, text: str) -> List[str]:
        """Extrahiert ICD-10 Codes aus Text."""
        # Pattern: A00.0 bis Z99.9
        pattern = r'[A-Z]\d{2}(?:\.\d{1,2})?'
        return re.findall(pattern, text)
    
    def _detect_gender(self, text: str) -> Optional[str]:
        """Erkennt Geschlecht aus Text."""
        text_lower = text.lower()
        
        male_indicators = ['patient', 'herr', 'mann', 'männlich', 'er ', ' er,', 'sein']
        female_indicators = ['patientin', 'frau', 'weiblich', 'sie ', ' sie,', 'ihr', 'schwanger']
        
        male_score = sum(1 for ind in male_indicators if ind in text_lower)
        female_score = sum(1 for ind in female_indicators if ind in text_lower)
        
        if female_score > male_score:
            return 'female'
        elif male_score > female_score:
            return 'male'
        return None
    
    def validate(self, qa: Dict) -> List[ValidationIssue]:
        """Validiert ICD-10 Codes in einer Q&A."""
        issues = []
        
        # Kombiniere alle Textfelder
        full_text = str(qa.get('frage', '')) + ' ' + str(qa.get('antwort', ''))
        
        # Extrahiere Codes
        codes = self._extract_icd_codes(full_text)
        
        if not codes:
            return issues  # Keine Codes zu prüfen
        
        # Erkenne Geschlecht
        gender = self._detect_gender(full_text)
        
        for code in codes:
            code_prefix = code[:3]
            
            # Geschlechtsprüfung
            if gender == 'female' and code_prefix in self.MALE_ONLY_CODES:
                issues.append(ValidationIssue(
                    validator="ICD10Validator",
                    severity=ValidationSeverity.ERROR,
                    message=f"GESCHLECHTS-INKONSISTENZ: {code} ({self.MALE_ONLY_CODES[code_prefix]}) bei weiblicher Patientin",
                    field="icd_code",
                    value=code,
                    suggestion="Prüfe Geschlecht des Patienten"
                ))
            
            if gender == 'male' and code_prefix in self.FEMALE_ONLY_CODES:
                issues.append(ValidationIssue(
                    validator="ICD10Validator",
                    severity=ValidationSeverity.ERROR,
                    message=f"GESCHLECHTS-INKONSISTENZ: {code} ({self.FEMALE_ONLY_CODES.get(code_prefix, 'weiblich-spezifisch')}) bei männlichem Patient",
                    field="icd_code",
                    value=code,
                    suggestion="Prüfe Geschlecht des Patienten"
                ))
        
        return issues


# ============================================================================
# 3. LAB VALUE VALIDATOR 🧪
# ============================================================================

class LabValueValidator:
    """
    Prüft Laborwerte auf Plausibilität.
    
    Erkennt:
    - Lebensbedrohliche Werte
    - Unplausible Werte
    - Fehlende Einheiten
    """
    
    # Referenzbereiche und kritische Grenzen
    # (min_normal, max_normal, critical_low, critical_high, einheit)
    LAB_RANGES = {
        'kalium': (3.5, 5.0, 2.5, 6.5, 'mmol/l'),
        'natrium': (135, 145, 120, 160, 'mmol/l'),
        'kreatinin': (0.6, 1.2, 0.3, 10.0, 'mg/dl'),
        'glucose': (70, 100, 40, 400, 'mg/dl'),
        'hämoglobin': (12, 17, 5, 20, 'g/dl'),
        'leukozyten': (4.0, 10.0, 1.0, 50.0, '/nl'),
        'thrombozyten': (150, 400, 20, 1000, '/nl'),
        'crp': (0, 5, 0, 200, 'mg/l'),
        'troponin': (0, 0.04, 0, 10, 'ng/ml'),
        'inr': (0.9, 1.1, 0.5, 5.0, ''),
        'ptt': (25, 35, 15, 100, 's'),
    }
    
    def __init__(self):
        self.logger = logging.getLogger("MedExamAI.LabValueValidator")
    
    def _extract_lab_values(self, text: str) -> List[Dict]:
        """Extrahiert Laborwerte aus Text."""
        values = []
        text_lower = text.lower()
        
        for lab_name, (min_n, max_n, crit_low, crit_high, unit) in self.LAB_RANGES.items():
            # Suche nach dem Laborwert
            patterns = [
                rf'{lab_name}[:\s]+(\d+(?:[.,]\d+)?)\s*{unit}',
                rf'{lab_name}[:\s]+(\d+(?:[.,]\d+)?)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = float(match.group(1).replace(',', '.'))
                    values.append({
                        'name': lab_name,
                        'value': value,
                        'unit': unit,
                        'normal_range': (min_n, max_n),
                        'critical_range': (crit_low, crit_high)
                    })
                    break
        
        return values
    
    def validate(self, qa: Dict) -> List[ValidationIssue]:
        """Validiert Laborwerte in einer Q&A."""
        issues = []
        
        full_text = str(qa.get('frage', '')) + ' ' + str(qa.get('antwort', ''))
        lab_values = self._extract_lab_values(full_text)
        
        for lab in lab_values:
            value = lab['value']
            crit_low, crit_high = lab['critical_range']
            min_n, max_n = lab['normal_range']
            
            if value < crit_low or value > crit_high:
                issues.append(ValidationIssue(
                    validator="LabValueValidator",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"KRITISCHER LABORWERT: {lab['name'].capitalize()} = {value} {lab['unit']} (Kritisch: <{crit_low} oder >{crit_high})",
                    field="laborwerte",
                    value=f"{value} {lab['unit']}",
                    suggestion=f"Lebensbedrohlich! Normalbereich: {min_n}-{max_n} {lab['unit']}"
                ))
            elif value < min_n or value > max_n:
                issues.append(ValidationIssue(
                    validator="LabValueValidator",
                    severity=ValidationSeverity.INFO,
                    message=f"Laborwert außerhalb Normbereich: {lab['name'].capitalize()} = {value} {lab['unit']}",
                    field="laborwerte",
                    value=f"{value} {lab['unit']}",
                    suggestion=f"Normalbereich: {min_n}-{max_n} {lab['unit']}"
                ))
        
        return issues


# ============================================================================
# 4. LOGICAL CONSISTENCY VALIDATOR 🧠
# ============================================================================

class LogicalConsistencyValidator:
    """
    Prüft auf logische Widersprüche.
    
    Erkennt:
    - Kontraindikationen
    - Widersprüchliche Aussagen
    - Unmögliche Kombinationen
    """
    
    # Kontraindikationen: (Medikament, Bedingung, Schweregrad)
    CONTRAINDICATIONS = [
        ('methotrexat', 'schwanger', ValidationSeverity.CRITICAL),
        ('methotrexat', 'schwangerschaft', ValidationSeverity.CRITICAL),
        ('ace-hemmer', 'schwanger', ValidationSeverity.CRITICAL),
        ('warfarin', 'schwanger', ValidationSeverity.CRITICAL),
        ('isotretinoin', 'schwanger', ValidationSeverity.CRITICAL),
        ('metformin', 'niereninsuffizienz', ValidationSeverity.ERROR),
        ('nsaid', 'niereninsuffizienz', ValidationSeverity.WARNING),
        ('nsaid', 'ulkus', ValidationSeverity.ERROR),
        ('betablocker', 'asthma', ValidationSeverity.WARNING),
        ('sulfonylharnstoff', 'niereninsuffizienz', ValidationSeverity.WARNING),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger("MedExamAI.LogicalConsistencyValidator")
    
    def validate(self, qa: Dict) -> List[ValidationIssue]:
        """Prüft logische Konsistenz."""
        issues = []
        
        full_text = (str(qa.get('frage', '')) + ' ' + str(qa.get('antwort', ''))).lower()
        
        for med, condition, severity in self.CONTRAINDICATIONS:
            if med in full_text and condition in full_text:
                issues.append(ValidationIssue(
                    validator="LogicalConsistencyValidator",
                    severity=severity,
                    message=f"KONTRAINDIKATION: {med.upper()} bei {condition.upper()}",
                    field="logik",
                    value=f"{med} + {condition}",
                    suggestion=f"{med.capitalize()} ist bei {condition} kontraindiziert!"
                ))
        
        return issues


# ============================================================================
# MEDICAL VALIDATION PIPELINE
# ============================================================================

class MedicalValidationPipeline:
    """
    Führt alle 4 Prüfer aus und erstellt Gesamtergebnis.
    """
    
    def __init__(self):
        self.validators = [
            DosageValidator(),
            ICD10Validator(),
            LabValueValidator(),
            LogicalConsistencyValidator(),
        ]
        self.logger = logging.getLogger("MedExamAI.ValidationPipeline")
    
    def validate_single(self, qa: Dict) -> ValidationResult:
        """Validiert einzelne Q&A durch alle Prüfer."""
        qa_id = qa.get('id', 'unknown')
        result = ValidationResult(qa_id=qa_id, is_valid=True)
        
        for validator in self.validators:
            issues = validator.validate(qa)
            for issue in issues:
                result.add_issue(issue)
        
        return result
    
    def validate_all(self, qa_list: List[Dict]) -> Dict:
        """Validiert alle Q&A und gibt Statistiken zurück."""
        self.logger.info(f"🛡️ Starte Medical Validation für {len(qa_list)} Q&A...")
        
        results = []
        stats = {
            'total': len(qa_list),
            'valid': 0,
            'invalid': 0,
            'quarantine': 0,
            'issues_by_severity': {s.value: 0 for s in ValidationSeverity},
            'issues_by_validator': {}
        }
        
        quarantine_list = []
        
        for qa in qa_list:
            result = self.validate_single(qa)
            results.append(result)
            
            if result.is_valid:
                stats['valid'] += 1
            else:
                stats['invalid'] += 1
            
            if result.quarantine:
                stats['quarantine'] += 1
                quarantine_list.append({
                    'qa_id': result.qa_id,
                    'issues': [asdict(i) if hasattr(i, '__dict__') else str(i) for i in result.issues]
                })
            
            for issue in result.issues:
                stats['issues_by_severity'][issue.severity.value] += 1
                validator_name = issue.validator
                stats['issues_by_validator'][validator_name] = stats['issues_by_validator'].get(validator_name, 0) + 1
        
        # Ausgabe
        print("\n" + "="*70)
        print("🛡️ MEDICAL VALIDATION REPORT")
        print("="*70)
        print(f"\n📊 ÜBERSICHT:")
        print(f"   Total Q&A:    {stats['total']}")
        print(f"   ✅ Valid:     {stats['valid']}")
        print(f"   ❌ Invalid:   {stats['invalid']}")
        print(f"   🔒 Quarantäne: {stats['quarantine']}")
        
        print(f"\n📈 ISSUES BY SEVERITY:")
        for severity, count in stats['issues_by_severity'].items():
            if count > 0:
                print(f"   {severity}: {count}")
        
        print(f"\n🔍 ISSUES BY VALIDATOR:")
        for validator, count in stats['issues_by_validator'].items():
            print(f"   {validator}: {count}")
        
        print("="*70)
        
        return {
            'stats': stats,
            'quarantine': quarantine_list,
            'results': results
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def validate_qa_file(input_file: str, output_file: str = "validation_results.json"):
    """Validiert Q&A Datei und speichert Ergebnisse."""
    import json
    from dataclasses import asdict
    
    # Laden
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'qa_pairs' in data:
        qa_list = data['qa_pairs']
    elif isinstance(data, list):
        qa_list = data
    else:
        qa_list = [data]
    
    # Validieren
    pipeline = MedicalValidationPipeline()
    results = pipeline.validate_all(qa_list)
    
    # Speichern
    output = {
        'stats': results['stats'],
        'quarantine': results['quarantine']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Ergebnisse gespeichert: {output_file}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python medical_validators.py <input_qa.json> [output.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "validation_results.json"
    
    validate_qa_file(input_file, output_file)
```

---

# 🎯 TEIL 4: INTEGRATION & WORKFLOW

## 4.1 Master Pipeline

Erstelle `run_full_pipeline.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Master Pipeline
==========================

Führt die komplette Verarbeitung aus:
1. Konvertierung ins Prüfungsformat
2. RAG Enrichment (Perplexity+Portkey)
3. Gold Standard Validierung
4. Medical Validation
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='MedExamAI Master Pipeline')
    parser.add_argument('--input', '-i', required=True, help='Input Q&A JSON')
    parser.add_argument('--gold', '-g', required=True, help='Gold Standard Ordner')
    parser.add_argument('--output-dir', '-o', default='output', help='Output Verzeichnis')
    parser.add_argument('--max-enrichments', type=int, default=100, help='Max RAG Enrichments')
    parser.add_argument('--skip-rag', action='store_true', help='RAG überspringen')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("🚀 MedExamAI MASTER PIPELINE")
    print("="*70)
    print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📥 Input: {args.input}")
    print(f"🏆 Gold Standard: {args.gold}")
    print(f"📁 Output: {output_dir}")
    
    # Step 1: Konvertierung
    print("\n" + "-"*70)
    print("📝 SCHRITT 1: Konvertierung ins Prüfungsformat")
    print("-"*70)
    # ... (Import und Ausführung von convert_to_exam_format.py)
    
    # Step 2: RAG Enrichment
    if not args.skip_rag:
        print("\n" + "-"*70)
        print("🤖 SCHRITT 2: RAG Enrichment (Perplexity+Portkey)")
        print("-"*70)
        # ... (Import und Ausführung von enrich_with_perplexity.py)
    
    # Step 3: Gold Standard Validierung
    print("\n" + "-"*70)
    print("🏆 SCHRITT 3: Gold Standard Validierung")
    print("-"*70)
    # ... (Import und Ausführung von gold_standard_comparator.py)
    
    # Step 4: Medical Validation
    print("\n" + "-"*70)
    print("🛡️ SCHRITT 4: Medical Validation (4 Prüfer)")
    print("-"*70)
    # ... (Import und Ausführung von medical_validators.py)
    
    print("\n" + "="*70)
    print("✅ PIPELINE ABGESCHLOSSEN")
    print(f"⏰ Ende: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()
```

---

# ✅ DEFINITION OF DONE

| Komponente | Kriterium | Status |
|------------|-----------|--------|
| **RAG Client** | Perplexity+Portkey funktioniert | ⏳ |
| **RAG Client** | Beide API Keys rotieren | ⏳ |
| **RAG Client** | Caching funktioniert | ⏳ |
| **RAG Client** | Budget Tracking aktiv | ⏳ |
| **Gold Standard** | Loader lädt alle Protokolle | ⏳ |
| **Gold Standard** | Matching findet >60% | ⏳ |
| **Gold Standard** | Missing Topics identifiziert | ⏳ |
| **Medical Valid.** | Dosage Validator funktioniert | ⏳ |
| **Medical Valid.** | ICD-10 Validator funktioniert | ⏳ |
| **Medical Valid.** | Lab Value Validator funktioniert | ⏳ |
| **Medical Valid.** | Logical Consistency funktioniert | ⏳ |
| **Medical Valid.** | Quarantäne-Liste erstellt | ⏳ |

---

# 🚀 STARTE JETZT

```bash
# 1. Erstelle die Ordnerstruktur
mkdir -p core/rag core/validation scripts output cache/rag logs/rag

# 2. Erstelle die Dateien (Code oben kopieren)

# 3. Teste RAG Client
python core/rag/perplexity_portkey_client.py

# 4. Teste Gold Standard Comparator
python core/validation/gold_standard_comparator.py \
  --gold /path/to/_GOLD_STANDARD \
  --generated output/kenntnisprufung_formatted.json

# 5. Teste Medical Validators
python core/validation/medical_validators.py \
  output/kenntnisprufung_formatted.json

# 6. Berichte nach jeder Komponente!
```

---

**Berichte nach Abschluss jeder Komponente mit:**
1. Funktioniert es?
2. Welche Ergebnisse?
3. Offene Probleme?
