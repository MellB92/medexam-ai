#!/usr/bin/env python3
"""Validiert korrigierte Antworten via Perplexity (Web-Check) mit Resume.

Input
- `_OUTPUT/batch_corrected_<RUN_ID>.json` (Default: neueste Datei)

Outputs (neu, Timestamp)
- `_OUTPUT/batch_validated_<RUN_ID>.json`
- `_OUTPUT/batch_validated_<RUN_ID>_checkpoint.jsonl`

Harte Constraints
- Keine Secrets loggen.
- `_OUTPUT/evidenz_antworten.json` wird nicht überschrieben.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


def _now_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _append_jsonl(path: Path, obj: Dict[str, Any], *, fsync: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        if fsync:
            os.fsync(f.fileno())


def _load_checkpoint_jsonl(path: Path) -> Dict[str, Dict[str, Any]]:
    done: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            rid = str(obj.get("id") or "").strip()
            if rid:
                done[rid] = obj
    return done


def _pick_latest(output_dir: Path, pattern: str) -> Path:
    candidates = sorted(
        output_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"Keine Dateien für Pattern: {pattern}")
    return candidates[0]


def _find_latest_checkpoint(output_dir: Path) -> Optional[Path]:
    candidates = list(output_dir.glob("batch_validated_*_checkpoint.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _run_id_from_checkpoint(path: Path) -> Optional[str]:
    m = re.match(r"batch_validated_(.+)_checkpoint\.jsonl$", path.name)
    return m.group(1) if m else None


def _load_env_fallback(dotenv_path: Path) -> None:
    """Best-effort: parse .env for PERPLEXITY_* vars (no printing)."""
    if not dotenv_path.exists():
        return
    prefix = "PERPLEXITY_"
    try:
        for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if not k.startswith(prefix):
                continue
            v = v.strip().strip("\"'")
            if not os.getenv(k) and v:
                os.environ[k] = v
    except Exception:
        return


def _get_perplexity_keys() -> List[str]:
    k1 = os.getenv("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY_1")
    k2 = os.getenv("PERPLEXITY_API_KEY_2")
    return [k for k in [k1, k2] if k]


def _perplexity_request(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_s: int,
) -> Dict[str, Any]:
    base_url = os.getenv("PERPLEXITY_API_BASE", "https://api.perplexity.ai").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    return resp.json()


def _extract_json_obj(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    candidate = text.strip()
    if "```" in candidate:
        if "```json" in candidate:
            start = candidate.find("```json") + len("```json")
            end = candidate.find("```", start)
            candidate = candidate[start:end].strip()
        else:
            start = candidate.find("```") + 3
            end = candidate.find("```", start)
            candidate = candidate[start:end].strip()
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", candidate)
    if not m:
        return None
    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _truncate_middle(text: str, max_chars: int = 2800, head: int = 1800) -> str:
    t = text or ""
    if len(t) <= max_chars:
        return t
    tail = max(0, max_chars - head)
    return t[:head] + "\n…\n" + t[-tail:]


def _system_prompt() -> str:
    return "\n".join(
        [
            "Du bist ein medizinischer Faktenprüfer für die deutsche Kenntnisprüfung.",
            "",
            "AUFGABE:",
            "Validiere die korrigierte Antwort auf:",
            "1) Faktische Richtigkeit",
            "2) Aktualität (Leitlinien 2024/2025, falls relevant)",
            "3) Vollständigkeit für Prüfungszwecke",
            "",
            "RECHERCHE:",
            "Nutze Web-Suche für aktuelle Quellen. Bevorzuge AWMF, RKI/STIKO,",
            "Fachgesellschaften. DocCheck/Flexikon nur sekundär.",
            "",
            "OUTPUT STRICT ALS JSON (kein Markdown, keine Erklärtexte):",
            "{",
            '  "verdict": "ok|maybe|problem",',
            '  "issues": ["..."],',
            '  "aktuelle_quellen": [{"titel": "...", "url": "...", "relevanz": "..."}],',
            '  "empfehlung": "..."',
            "}",
            "",
            "FORMAT-REGELN (damit das JSON NICHT abgeschnitten wird):",
            "- issues: maximal 4 Punkte, je 1 Satz.",
            "- aktuelle_quellen: maximal 4 Quellen.",
            "- empfehlung: maximal 2 Sätze.",
            "- Keine Code-Fences (```), keine zusätzlichen Texte außerhalb des JSON.",
        ]
    )


def _user_prompt(item: Dict[str, Any]) -> str:
    frage = str(item.get("frage") or "").strip()
    ans = str(item.get("antwort_korrigiert") or "").strip()
    issues = item.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    issues_txt = "\n".join([f"- {str(x).strip()}" for x in issues[:10] if str(x).strip()])
    return "\n".join(
        [
            "FRAGE:",
            frage,
            "",
            "KORRIGIERTE ANTWORT:",
            _truncate_middle(ans, 2600, 1600),
            "",
            "ALT-PROBLEME (zur Orientierung):",
            issues_txt or "- (keine Issues geliefert)",
            "",
            "Bitte bewerte und liefere STRICT JSON.",
        ]
    )


def _salvage_truncated_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Best-effort Salvage für abgeschnittenes JSON (fehlende schließende Klammern).

    Liefert mindestens `verdict` und optional teil-extrahierte `issues`.
    """
    if not raw_text:
        return None
    txt = raw_text.strip()
    # Optional: Code-Fences entfernen
    if txt.startswith("```"):
        first_nl = txt.find("\n")
        if first_nl != -1:
            txt = txt[first_nl + 1 :]
        last = txt.rfind("```")
        if last != -1:
            txt = txt[:last].strip()

    m = re.search(r'"verdict"\s*:\s*"(?P<v>ok|maybe|problem)"', txt, re.IGNORECASE)
    if not m:
        return None
    verdict = m.group("v").lower()

    issues: List[str] = []
    key = '"issues"'
    pos = txt.find(key)
    if pos != -1:
        start = txt.find("[", pos)
        if start != -1:
            dec = json.JSONDecoder()
            i = start + 1
            while i < len(txt):
                while i < len(txt) and txt[i] in " \t\r\n,":
                    i += 1
                if i >= len(txt) or txt[i] == "]":
                    break
                try:
                    val, end = dec.raw_decode(txt[i:])
                except Exception:
                    break
                if isinstance(val, str) and val.strip():
                    issues.append(val.strip())
                i += end
                if len(issues) >= 8:
                    break

    return {
        "verdict": verdict,
        "issues": issues[:8],
        "aktuelle_quellen": [],
        "empfehlung": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validiert batch_corrected via Perplexity.")
    parser.add_argument("--input", default="", help="batch_corrected JSON")
    parser.add_argument("--run-id", default="", help="Run-ID (für Dateinamen)")
    parser.add_argument("--resume", action="store_true", help="Resume via Checkpoint")
    parser.add_argument("--model", default="sonar-pro", help="Perplexity Model (default: sonar-pro)")
    parser.add_argument("--max-tokens", type=int, default=1200, help="Max Tokens pro Call")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout (s)")
    parser.add_argument("--sleep", type=float, default=0.5, help="Pause zwischen Requests (s)")
    parser.add_argument("--limit", type=int, default=0, help="Optional: nur N Items validieren")
    parser.add_argument("--fsync", action="store_true", help="Checkpoint fsync")
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Items mit verdict=error erneut versuchen (überschreibt per neuem Checkpoint-Eintrag).",
    )
    args = parser.parse_args()

    _load_env_fallback(PROJECT_ROOT / ".env")
    keys = _get_perplexity_keys()
    if not keys:
        raise SystemExit(
            "Keine PERPLEXITY_API_KEY gefunden (ENV/.env). "
            "Setze PERPLEXITY_API_KEY und starte erneut."
        )

    if args.input:
        input_path = Path(args.input)
    else:
        input_path = _pick_latest(OUTPUT_DIR, "batch_corrected_*.json")
    if not input_path.exists():
        raise SystemExit(f"Input fehlt: {input_path}")

    run_id = args.run_id.strip()
    checkpoint_path: Optional[Path] = None
    if args.resume and not run_id:
        checkpoint_path = _find_latest_checkpoint(OUTPUT_DIR)
        if checkpoint_path:
            run_id = _run_id_from_checkpoint(checkpoint_path) or ""
    if not run_id:
        run_id = _now_run_id()

    out_path = OUTPUT_DIR / f"batch_validated_{run_id}.json"
    ck_path = OUTPUT_DIR / f"batch_validated_{run_id}_checkpoint.jsonl"
    if checkpoint_path:
        ck_path = checkpoint_path

    payload = _read_json(input_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Input muss Objekt mit `items` sein")

    items: List[Dict[str, Any]] = [x for x in payload["items"] if isinstance(x, dict)]

    done = _load_checkpoint_jsonl(ck_path) if args.resume else {}
    sys_prompt = _system_prompt()

    max_new = int(args.limit) if args.limit and int(args.limit) > 0 else 0
    new_processed = 0

    rng = random.Random(0)

    for n, item in enumerate(items, start=1):
        rid = str(item.get("id") or "").strip()
        if not rid:
            continue
        if rid in done:
            if not args.retry_errors:
                continue
            existing = done.get(rid, {})
            v0 = str(existing.get("verdict") or "").strip().lower() if isinstance(existing, dict) else ""
            if v0 != "error":
                continue
            # Salvage ohne API call versuchen
            meta0 = existing.get("__meta__", {}) if isinstance(existing.get("__meta__"), dict) else {}
            raw0 = str(meta0.get("raw_response") or "")
            salv0 = _salvage_truncated_json(raw0)
            if salv0 and str(salv0.get("verdict") or "").strip():
                out_item = {
                    "id": rid,
                    "index": existing.get("index"),
                    "verdict": salv0.get("verdict"),
                    "issues": salv0.get("issues", []),
                    "aktuelle_quellen": salv0.get("aktuelle_quellen", []),
                    "empfehlung": salv0.get("empfehlung", ""),
                    "__meta__": {"raw_response": raw0, "note": "salvaged_from_truncated_json"},
                }
                _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
                done[rid] = out_item
                new_processed += 1
                continue
            # sonst: re-run via API (fall-through)

        # Wenn keine korrigierte Antwort vorliegt -> automatisch problem
        ans = str(item.get("antwort_korrigiert") or "").strip()
        if not ans:
            out_item = {
                "id": rid,
                "index": item.get("index"),
                "verdict": "problem",
                "issues": ["Keine korrigierte Antwort vorhanden (Upstream-Fehler)."],
                "aktuelle_quellen": [],
                "empfehlung": "Batch-Korrektur erneut ausführen oder manuell prüfen.",
                "__meta__": {"error": "missing_answer"},
            }
            _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
            new_processed += 1
            continue

        user_prompt = _user_prompt(item)
        api_key = keys[0] if len(keys) == 1 else keys[rng.randrange(0, len(keys))]

        err: Optional[str] = None
        parsed: Optional[Dict[str, Any]] = None
        raw_text = ""

        for attempt in range(1, 4):
            try:
                data = _perplexity_request(
                    api_key=api_key,
                    model=args.model,
                    system_prompt=sys_prompt,
                    user_prompt=user_prompt,
                    max_tokens=int(args.max_tokens),
                    timeout_s=int(args.timeout),
                )
                raw_text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                parsed = _extract_json_obj(raw_text)
                if parsed:
                    break
                err = "parse_failed"
            except Exception as e:
                err = str(e)
                time.sleep(2 * attempt)

        if not parsed:
            salv = _salvage_truncated_json(raw_text)
            if salv and str(salv.get("verdict") or "").strip():
                out_item = {
                    "id": rid,
                    "index": item.get("index"),
                    "verdict": str(salv.get("verdict") or "maybe").strip().lower(),
                    "issues": salv.get("issues", []),
                    "aktuelle_quellen": salv.get("aktuelle_quellen", []),
                    "empfehlung": salv.get("empfehlung", ""),
                    "__meta__": {"raw_response": raw_text, "note": "salvaged_from_truncated_json"},
                }
                _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
                new_processed += 1
                continue
            out_item = {
                "id": rid,
                "index": item.get("index"),
                "verdict": "error",
                "issues": [err or "unbekannt"],
                "aktuelle_quellen": [],
                "empfehlung": "",
                "__meta__": {"raw_response": raw_text},
            }
            _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
            new_processed += 1
            continue

        verdict = str(parsed.get("verdict") or "").strip().lower()
        if verdict not in {"ok", "maybe", "problem"}:
            verdict = "maybe"

        out_item = {
            "id": rid,
            "index": item.get("index"),
            "verdict": verdict,
            "issues": parsed.get("issues", []) if isinstance(parsed.get("issues"), list) else [],
            "aktuelle_quellen": parsed.get("aktuelle_quellen", [])
            if isinstance(parsed.get("aktuelle_quellen"), list)
            else [],
            "empfehlung": str(parsed.get("empfehlung") or "").strip(),
            "__meta__": {"raw_response": raw_text},
        }

        _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
        new_processed += 1

        if args.sleep and float(args.sleep) > 0:
            time.sleep(float(args.sleep))

        if n % 10 == 0:
            snap = _load_checkpoint_jsonl(ck_path)
            counts = {"ok": 0, "maybe": 0, "problem": 0, "error": 0}
            for x in snap.values():
                v = str(x.get("verdict") or "").strip().lower()
                if v in counts:
                    counts[v] += 1
            print(
                f"[{n}/{len(items)}] ok={counts['ok']} maybe={counts['maybe']} "
                f"problem={counts['problem']} err={counts['error']}"
            )

        if max_new and new_processed >= max_new:
            break

    snap = _load_checkpoint_jsonl(ck_path)
    processed = list(snap.values())
    processed.sort(key=lambda x: int(x.get("index") or 0))
    counts = {"ok": 0, "maybe": 0, "problem": 0, "error": 0}
    for x in processed:
        v = str(x.get("verdict") or "").strip().lower()
        if v in counts:
            counts[v] += 1

    final = {
        "generated_at": datetime.now().isoformat(),
        "run_id": run_id,
        "source_input": input_path.name,
        "model": args.model,
        "total_processed": len(processed),
        "summary": counts,
        "items": processed,
    }
    _write_json(out_path, final)

    print("Batch-Validierung abgeschlossen.")
    print(f"Input: {input_path}")
    print(f"Checkpoint: {ck_path}")
    print(f"Output: {out_path}")
    print(
        f"Processed: {len(processed)} | summary={counts} "
        f"| new_in_run={new_processed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


