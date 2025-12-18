"""Filesystem backed prompt cache for high reuse prompts."""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class PromptCache:
    """Lightweight persistent cache for prompt responses."""

    def __init__(self, cache_path: str = "cache/prompt_cache.json", max_entries: int = 2000) -> None:
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.cache_path.is_file():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._store = data
            except json.JSONDecodeError:
                self._store = {}

    def _persist(self) -> None:
        self.cache_path.write_text(json.dumps(self._store, ensure_ascii=False, indent=2), encoding="utf-8")

    def _evict_if_needed(self) -> None:
        if len(self._store) <= self.max_entries:
            return
        # Evict oldest entries based on insertion order
        while len(self._store) > self.max_entries:
            first_key = next(iter(self._store))
            self._store.pop(first_key, None)

    def _hash_messages(self, messages: Any, scope: str) -> str:
        payload = json.dumps({"messages": messages, "scope": scope}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, messages: Any, scope: str) -> Optional[Dict[str, Any]]:
        cache_key = self._hash_messages(messages, scope)
        with self._lock:
            entry = self._store.get(cache_key)
            if entry:
                entry["hits"] = entry.get("hits", 0) + 1
        return entry

    def set(self, messages: Any, scope: str, response: Dict[str, Any]) -> None:
        cache_key = self._hash_messages(messages, scope)
        payload = {
            "response": response,
            "hits": 1,
        }
        with self._lock:
            self._store[cache_key] = payload
            self._evict_if_needed()
            self._persist()
