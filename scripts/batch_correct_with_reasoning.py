#!/usr/bin/env python3
"""Batch-Korrektur der Review-Items via LLM (mit Checkpoint/Resume).

Input
- `_OUTPUT/batch_input_prepared_*.json` (Default: neueste Datei)

Output (neu, Timestamp)
- `_OUTPUT/batch_corrected_<RUN_ID>.json`
- `_OUTPUT/batch_corrected_<RUN_ID>_checkpoint.jsonl`

Harte Constraints
- Keine Secrets loggen.
- `_OUTPUT/evidenz_antworten.json` wird nicht überschrieben.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Repo-Root in sys.path, damit `core.*` importierbar ist.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.unified_api_client import UnifiedAPIClient

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
    candidates = list(output_dir.glob("batch_corrected_*_checkpoint.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _run_id_from_checkpoint(path: Path) -> Optional[str]:
    m = re.match(r"batch_corrected_(.+)_checkpoint\.jsonl$", path.name)
    return m.group(1) if m else None


def _truncate(text: str, max_chars: int = 1800) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "…"


def _system_prompt() -> str:
    return "\n".join(
        [
            "Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.",
            "",
            "AUFGABE:",
            "Korrigiere die Antwort basierend auf den identifizierten Problemen.",
            "",
            "REGELN:",
            "1) Nutze nur evidenzbasierte Informationen.",
            "2) Bevorzuge deutsche Quellen: AWMF, RKI/STIKO, Fachinfo.de.",
            "3) Wenn Dosierungen genannt werden: nur mit Fachinfo.de-Beleg.",
            "4) Antworte auf Deutsch, prüfungsrelevant, präzise.",
            "",
            "OUTPUT STRICT ALS JSON (kein Markdown, keine Erklärtexte):",
            "{",
            '  "korrigierte_antwort": "…",',
            '  "verwendete_quellen": [',
            '    {"titel": "...", "reg_nr": "...", "url": "..."}',
            "  ],",
            '  "aenderungen": ["..."],',
            '  "konfidenz": 0.0',
            "}",
        ]
    )


def _user_prompt(item: Dict[str, Any]) -> str:
    frage = str(item.get("frage") or "").strip()
    antwort = str(item.get("antwort_original") or "").strip()
    issues = item.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    issues_txt = "\n".join([f"- {str(x).strip()}" for x in issues[:12] if str(x).strip()])
    fix = str(item.get("optional_fix_snippet") or "").strip()
    fach = str(item.get("fachgebiet") or "").strip()
    prio = str(item.get("priority") or "").strip()

    ctx = item.get("context", {}) if isinstance(item.get("context"), dict) else {}
    ctx_lines = ctx.get("context_lines", []) if isinstance(ctx.get("context_lines"), list) else []
    ctx_text = "\n".join([f"- {str(x).strip()}" for x in ctx_lines[:8] if str(x).strip()])

    gl = item.get("zugeordnete_leitlinien", [])
    if not isinstance(gl, list):
        gl = []
    gl_txt = "\n".join(
        [
            f"- {g.get('titel','')} (Reg: {g.get('reg_nr','')}) [{g.get('pfad','')}]"
            for g in gl[:6]
            if isinstance(g, dict)
        ]
    )

    parts = [
        "FRAGE:",
        frage,
        "",
        f"FACHGEBIET: {fach} | PRIORITÄT: {prio}",
        "",
        "ORIGINAL-ANTWORT:",
        _truncate(antwort, 2600),
        "",
        "IDENTIFIZIERTE PROBLEME:",
        issues_txt or "- (keine Issues geliefert)",
        "",
    ]
    if ctx_text:
        parts.extend(["KONTEXT (Goldstandard-Auszug):", ctx_text, ""])
    if fix:
        parts.extend(["VORGESCHLAGENE KORREKTUR (als Hilfe):", _truncate(fix, 1200), ""])
    if gl_txt:
        parts.extend(["ZUGEORDNETE LEITLINIEN (lokal):", gl_txt, ""])

    parts.append("Bitte korrigiere die Antwort gemäß Regeln und liefere STRICT JSON.")
    return "\n".join(parts)


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        # Entferne erste Fence-Zeile
        first_nl = t.find("\n")
        if first_nl != -1:
            t = t[first_nl + 1 :]
        # Entferne letzte Fence
        last = t.rfind("```")
        if last != -1:
            t = t[:last].strip()
    return t.strip()


def _escape_unescaped_quotes(s: str) -> str:
    out = []
    for i, ch in enumerate(s):
        if ch != '"':
            out.append(ch)
            continue
        # Count backslashes directly before i
        bs = 0
        j = i - 1
        while j >= 0 and s[j] == "\\":
            bs += 1
            j -= 1
        if bs % 2 == 0:
            out.append('\\"')
        else:
            out.append('"')
    return "".join(out)


def _salvage_from_raw(raw_response: str) -> Dict[str, Any]:
    """Best-effort: extrahiert Felder aus (evtl. invalidem) JSON."""
    raw = _strip_code_fences(raw_response)
    out: Dict[str, Any] = {}

    # korrigierte_antwort (String)
    k = '"korrigierte_antwort"'
    vq = '"verwendete_quellen"'
    pos_k = raw.find(k)
    pos_vq = raw.find(vq)
    if pos_k != -1 and pos_vq != -1 and pos_k < pos_vq:
        pos_colon = raw.find(":", pos_k)
        pos_q1 = raw.find('"', pos_colon + 1)
        end_q = raw.rfind('",', pos_q1, pos_vq)
        if pos_q1 != -1 and end_q != -1 and pos_q1 < end_q:
            val = raw[pos_q1 + 1 : end_q]
            val_esc = _escape_unescaped_quotes(val)
            try:
                out["korrigierte_antwort"] = json.loads('"' + val_esc + '"')
            except Exception:
                out["korrigierte_antwort"] = val.strip()

    def extract_array(key_name: str, next_key: str) -> List[Any]:
        pos_a = raw.find(f'"{key_name}"')
        if pos_a == -1:
            return []
        pos_start = raw.find("[", pos_a)
        if pos_start == -1:
            return []
        # Suche Ende via Klammer-Zählung
        depth = 0
        for i in range(pos_start, len(raw)):
            ch = raw[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    chunk = raw[pos_start : i + 1]
                    try:
                        parsed = json.loads(chunk)
                        return parsed if isinstance(parsed, list) else []
                    except Exception:
                        return []
        return []

    out["verwendete_quellen"] = extract_array("verwendete_quellen", "aenderungen")
    out["aenderungen"] = extract_array("aenderungen", "konfidenz")

    m = re.search(r'"konfidenz"\s*:\s*([0-9]+(?:\.[0-9]+)?)', raw)
    if m:
        try:
            out["konfidenz"] = float(m.group(1))
        except Exception:
            pass

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-Korrektur (LLM) mit Resume.")
    parser.add_argument("--input", default="", help="batch_input_prepared JSON")
    parser.add_argument("--run-id", default="", help="Run-ID (für Dateinamen)")
    parser.add_argument("--resume", action="store_true", help="Resume via Checkpoint")
    parser.add_argument("--provider", default="requesty", help="LLM Provider (default: requesty)")
    parser.add_argument("--model", default="openai/o4-mini", help="LLM Model (default: openai/o4-mini)")
    parser.add_argument("--max-tokens", type=int, default=2000, help="Max Tokens pro Call (default: 2000)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature (default: 0.0)")
    parser.add_argument("--sleep", type=float, default=0.5, help="Pause zwischen Requests (s)")
    parser.add_argument("--limit", type=int, default=0, help="Optional: nur N Items verarbeiten")
    parser.add_argument("--fsync", action="store_true", help="Checkpoint fsync (langsamer, aber sicherer)")
    args = parser.parse_args()

    if args.input:
        input_path = Path(args.input)
    else:
        input_path = _pick_latest(OUTPUT_DIR, "batch_input_prepared_*.json")
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

    out_path = OUTPUT_DIR / f"batch_corrected_{run_id}.json"
    ck_path = OUTPUT_DIR / f"batch_corrected_{run_id}_checkpoint.jsonl"
    if checkpoint_path:
        ck_path = checkpoint_path

    payload = _read_json(input_path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Input muss Objekt mit `items` sein")

    items: List[Dict[str, Any]] = [x for x in payload["items"] if isinstance(x, dict)]

    done = _load_checkpoint_jsonl(ck_path) if args.resume else {}

    client = UnifiedAPIClient()
    sys_prompt = _system_prompt()

    max_new = int(args.limit) if args.limit and int(args.limit) > 0 else 0
    new_processed = 0

    for n, item in enumerate(items, start=1):
        rid = str(item.get("id") or "").strip()
        if not rid:
            continue
        if rid in done:
            existing = done.get(rid, {})
            if isinstance(existing, dict):
                existing_ans = str(existing.get("antwort_korrigiert") or "").strip()
                if existing_ans:
                    continue
                # Versuche ohne API: salvage aus raw_response (häufig invalid JSON)
                ex_meta = existing.get("__meta__", {}) if isinstance(existing.get("__meta__"), dict) else {}
                ex_raw = str(ex_meta.get("raw_response") or "")
                if ex_raw:
                    salv = _salvage_from_raw(ex_raw)
                    salv_ans = str(salv.get("korrigierte_antwort") or "").strip()
                    if salv_ans:
                        updated_item = dict(existing)
                        updated_item["antwort_korrigiert"] = salv_ans
                        if isinstance(salv.get("verwendete_quellen"), list):
                            updated_item["verwendete_quellen"] = salv.get("verwendete_quellen")
                        if isinstance(salv.get("aenderungen"), list):
                            updated_item["aenderungen"] = salv.get("aenderungen")
                        if salv.get("konfidenz") is not None:
                            updated_item["konfidenz"] = salv.get("konfidenz")
                        um = updated_item.get("__meta__", {})
                        if isinstance(um, dict):
                            um["error"] = um.get("error") or "json_salvaged"
                        _append_jsonl(ck_path, updated_item, fsync=bool(args.fsync))
                        done[rid] = updated_item
                        new_processed += 1
                        continue

        prompt = _user_prompt(item)
        result: Dict[str, Any] = {}
        err: Optional[str] = None
        try:
            result = client.complete(
                prompt=prompt,
                provider=args.provider,
                model=args.model,
                max_tokens=int(args.max_tokens),
                temperature=float(args.temperature),
                system_prompt=sys_prompt,
            )
        except Exception as e:
            err = str(e)
            result = {}

        korr = str(result.get("korrigierte_antwort") or "").strip()
        quellen = result.get("verwendete_quellen", [])
        aend = result.get("aenderungen", [])
        konf = result.get("konfidenz", None)
        meta = result.get("__meta__", {}) if isinstance(result.get("__meta__"), dict) else {}

        # Fallback: teilweise Extraktion aus raw_response, falls JSON invalid war.
        raw_resp = str(meta.get("raw_response") or "")
        if not korr and raw_resp:
            salv = _salvage_from_raw(raw_resp)
            korr = str(salv.get("korrigierte_antwort") or "").strip()
            if korr:
                quellen = salv.get("verwendete_quellen", []) or []
                aend = salv.get("aenderungen", []) or []
                konf = salv.get("konfidenz", konf)
                err = err or "json_salvaged"

        out_item: Dict[str, Any] = {
            "id": rid,
            "index": item.get("index"),
            "frage": item.get("frage"),
            "fachgebiet": item.get("fachgebiet"),
            "study_status": item.get("study_status"),
            "priority": item.get("priority"),
            "antwort_original": item.get("antwort_original"),
            "antwort_korrigiert": korr,
            "verwendete_quellen": quellen if isinstance(quellen, list) else [],
            "aenderungen": aend if isinstance(aend, list) else [],
            "konfidenz": konf,
            "__meta__": {
                "provider": meta.get("provider"),
                "model": meta.get("model"),
                "usage": meta.get("usage", {}),
                "cost": meta.get("cost", 0.0),
                "budget_remaining": meta.get("budget_remaining"),
                "raw_response": meta.get("raw_response", ""),
                "error": err,
            },
        }

        _append_jsonl(ck_path, out_item, fsync=bool(args.fsync))
        new_processed += 1

        if args.sleep and float(args.sleep) > 0:
            time.sleep(float(args.sleep))

        if n % 10 == 0:
            snap = _load_checkpoint_jsonl(ck_path)
            ok_now = sum(
                1
                for x in snap.values()
                if isinstance(x, dict) and str(x.get("antwort_korrigiert") or "").strip()
            )
            err_now = len(snap) - ok_now
            cost_now = 0.0
            for x in snap.values():
                m = x.get("__meta__", {}) if isinstance(x, dict) else {}
                try:
                    cost_now += float(m.get("cost") or 0.0)
                except Exception:
                    pass
            print(
                f"[scan {n}/{len(items)}] new={new_processed} "
                f"done={len(snap)} ok={ok_now} err={err_now} "
                f"cost≈{cost_now:.2f} USD"
            )

        if max_new and new_processed >= max_new:
            break

    # Final-Snapshot aus Checkpoint schreiben (enthält alle Runs)
    snap = _load_checkpoint_jsonl(ck_path)
    processed = list(snap.values())
    processed.sort(key=lambda x: int(x.get("index") or 0))

    total_cost = 0.0
    total_ok = 0
    for x in processed:
        if str(x.get("antwort_korrigiert") or "").strip():
            total_ok += 1
        m = x.get("__meta__", {}) if isinstance(x, dict) else {}
        try:
            total_cost += float(m.get("cost") or 0.0)
        except Exception:
            pass
    total_err = len(processed) - total_ok

    final = {
        "generated_at": datetime.now().isoformat(),
        "run_id": run_id,
        "source_input": input_path.name,
        "provider": args.provider,
        "model": args.model,
        "total_processed": len(processed),
        "total_cost_usd": round(total_cost, 4),
        "ok": total_ok,
        "errors": total_err,
        "items": processed,
    }
    _write_json(out_path, final)

    print("Batch-Korrektur abgeschlossen.")
    print(f"Input: {input_path}")
    print(f"Checkpoint: {ck_path}")
    print(f"Output: {out_path}")
    print(
        f"Processed: {len(processed)} | ok={total_ok} err={total_err} "
        f"| new_in_run={new_processed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


