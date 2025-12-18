#!/usr/bin/env python3
"""Perplexity-Faktencheck (Stichprobe) – schreibt nur Findings.

Ziel
- Keine Änderungen an _OUTPUT/evidenz_antworten.json
- Perplexity soll pro Frage ausschließlich JSON liefern (ok|maybe|problem)

Sample-Strategie
- Immer alle Einträge aus
  _OUTPUT/problematic_meaningful_from_full_validation.json (erwartet: 12)
- Auffüllen auf N mit zufälligen \"meaningful\" Fragen aus
  _OUTPUT/meaningful_missing.json (seed fix)

Outputs
- _OUTPUT/perplexity_factcheck_sample_<YYYYMMDD_HHMM>.json
- _OUTPUT/perplexity_factcheck_sample_<YYYYMMDD_HHMM>.md

Hinweise
- .env wird via import core.web_search geladen (python-dotenv), zusätzlich
  Fallback-Parser.
- Keys werden niemals geloggt.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# IMPORTANT: loads .env (optional) via python-dotenv inside core.web_search
# (and keeps key handling centralized)
try:  # pragma: no cover
    import core.web_search  # noqa: F401
except Exception:
    # Hard fail ist nicht nötig – wir haben einen .env Fallback-Parser.
    pass


PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _checkpoint_path_for_run(output_dir: Path, run_id: str) -> Path:
    filename = f"perplexity_factcheck_sample_{run_id}_checkpoint.jsonl"
    return output_dir / filename


def _find_latest_checkpoint(output_dir: Path) -> Optional[Path]:
    candidates = list(output_dir.glob("perplexity_factcheck_sample_*_checkpoint.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _run_id_from_checkpoint_path(path: Path) -> Optional[str]:
    m = re.match(
        r"perplexity_factcheck_sample_(\d{8}_\d{4})_checkpoint\.jsonl$",
        path.name,
    )
    return m.group(1) if m else None


def _load_checkpoint_jsonl(path: Path) -> Dict[int, Dict[str, Any]]:
    """Loads checkpoint lines into a dict keyed by index_in_evidenz_antworten."""
    results_by_index: Dict[int, Dict[str, Any]] = {}
    if not path.exists():
        return results_by_index
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
            idx = obj.get("index_in_evidenz_antworten")
            if isinstance(idx, int):
                results_by_index[idx] = obj
    return results_by_index


def _append_checkpoint_jsonl(
    path: Path,
    obj: Dict[str, Any],
    *,
    fsync: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        if fsync:
            os.fsync(f.fileno())


def _normalize_whitespace(text: str) -> str:
    return " ".join((text or "").strip().split())


def _norm_key(text: str) -> str:
    return _normalize_whitespace(text).lower()


def _truncate_middle(
    text: str,
    max_chars: int = 2600,
    head: int = 1700,
) -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    tail = max(0, max_chars - head)
    return text[:head] + "\n…\n" + text[-tail:]


def _load_env_fallback(dotenv_path: Path) -> None:
    """Fallback: parse .env if python-dotenv isn't installed.

    Loads only PERPLEXITY_* variables (does not print values).
    """

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
            # keep quotes if present
            v = v.strip().strip("\"'")
            if not os.getenv(k) and v:
                os.environ[k] = v
    except Exception:
        # silent – we only use this as best-effort
        return


def _get_perplexity_keys() -> List[str]:
    key_1 = os.getenv("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY_1")
    key_2 = os.getenv("PERPLEXITY_API_KEY_2")
    return [k for k in [key_1, key_2] if k]


def _perplexity_request(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_s: int,
) -> Dict[str, Any]:
    base_url = os.getenv(
        "PERPLEXITY_API_BASE",
        "https://api.perplexity.ai",
    ).rstrip("/")
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

    # remove common fences
    if "```" in candidate:
        # prefer ```json
        if "```json" in candidate:
            start = candidate.find("```json") + len("```json")
            end = candidate.find("```", start)
            candidate = candidate[start:end].strip()
        else:
            # first fenced block
            start = candidate.find("```") + 3
            end = candidate.find("```", start)
            candidate = candidate[start:end].strip()

    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    # last resort: try to capture a JSON object
    m = re.search(r"\{[\s\S]*\}", candidate)
    if not m:
        return None

    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


@dataclass
class SampleItem:
    index_in_evidenz: int
    frage: str
    antwort: str
    source_file: str


def _load_main_index(
    main_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    data = _read_json(main_path)
    if not isinstance(data, list):
        raise SystemExit(f"Main JSON muss eine Liste sein: {main_path}")

    norm_index: Dict[str, int] = {}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        q = (item.get("frage") or item.get("question") or "").strip()
        if not q:
            continue
        nk = _norm_key(q)
        if nk not in norm_index:
            norm_index[nk] = i

    return data, norm_index


def _collect_problematic_questions(
    problematic_path: Path,
) -> List[Dict[str, Any]]:
    data = _read_json(problematic_path)
    if not isinstance(data, list):
        raise SystemExit(f"Problematic JSON muss eine Liste sein: {problematic_path}")
    # Keep original dicts, but we only rely on `frage` and optional index.
    return [
        d for d in data if isinstance(d, dict) and (d.get("frage") or d.get("question"))
    ]


def _collect_meaningful_questions(meaningful_path: Path) -> List[str]:
    data = _read_json(meaningful_path)
    if not isinstance(data, list):
        raise SystemExit(f"Meaningful JSON muss eine Liste sein: {meaningful_path}")

    questions: List[str] = []
    for item in data:
        if isinstance(item, dict):
            q = (item.get("frage") or item.get("question") or "").strip()
        else:
            q = str(item).strip()
        if q:
            questions.append(q)
    return questions


def _build_sample(
    *,
    main_data: List[Dict[str, Any]],
    main_norm_index: Dict[str, int],
    problematic: List[Dict[str, Any]],
    meaningful_questions: List[str],
    sample_size: int,
    seed: int,
) -> Tuple[List[SampleItem], List[str]]:
    # 1) start with all problematic
    selected_norm: set[str] = set()
    sample: List[SampleItem] = []
    warnings: List[str] = []

    def add_question(q: str) -> None:
        nq = _norm_key(q)
        if not nq or nq in selected_norm:
            return
        idx = main_norm_index.get(nq)
        if idx is None:
            warnings.append(f"not_found_in_main: {q[:120]}")
            return
        entry = main_data[idx]
        ans = (entry.get("antwort") or entry.get("answer") or "").strip()
        frage_text = (entry.get("frage") or entry.get("question") or q).strip()
        sample.append(
            SampleItem(
                index_in_evidenz=idx,
                frage=frage_text,
                antwort=ans,
                source_file=(entry.get("source_file") or "").strip(),
            )
        )
        selected_norm.add(nq)

    for p in problematic:
        q = (p.get("frage") or p.get("question") or "").strip()
        if q:
            add_question(q)

    if sample_size < len(sample):
        raise SystemExit(
            "sample_size ist kleiner als Anzahl problematischer Einträge: "
            f"{sample_size} < {len(sample)}"
        )

    # 2) fill with random meaningful
    rnd = random.Random(seed)
    pool = [q for q in meaningful_questions if _norm_key(q) not in selected_norm]
    rnd.shuffle(pool)

    for q in pool:
        if len(sample) >= sample_size:
            break
        add_question(q)

    if len(sample) < sample_size:
        warnings.append(f"sample_short: requested={sample_size} got={len(sample)}")

    return sample, warnings


def _build_prompts(frage: str, antwort: str) -> Tuple[str, str]:
    schema = (
        "{"
        '"verdict": "ok|maybe|problem", '
        '"issues": ["..."], '
        '"suggested_sources": ['
        '{"title": "...", "url": "...", "why": "..."}'
        "], "
        '"optional_fix_snippet": "..."'
        "}"
    )
    system_prompt = (
        "Du bist ein medizinischer Faktenprüfer für die deutsche "
        "Kenntnisprüfung. "
        "Bewerte die Antwort auf faktische Richtigkeit, Leitliniennähe und "
        "prüfungsrelevante Vollständigkeit. "
        "Nutze Web-Recherche nur soweit nötig. "
        "Bevorzuge AWMF, RKI, PEI, Fachgesellschaften (ESC/ERS/DGIM/DKG), "
        "DocCheck/Flexikon als sekundär. "
        "Wenn die Frage ohne Kontext nicht prüfbar ist (z.B. Bild fehlt), "
        "setze verdict=maybe und liste, welche Infos fehlen.\n\n"
        "GIB NUR EIN JSON-OBJEKT zurück (keine Markdown-Fences, "
        "kein Text außenrum).\n"
        "Schema:\n" + schema + "\n"
        "optional_fix_snippet nur, wenn verdict=problem oder maybe mit "
        "konkreter Korrektur."
    )

    user_prompt = (
        "Prüfe diese Frage-Antwort-Kombination.\n\n"
        f"FRAGE:\n{_truncate_middle(frage, max_chars=2200, head=1500)}\n\n"
        f"ANTWORT:\n{_truncate_middle(antwort, max_chars=3000, head=1900)}\n"
    )
    return system_prompt, user_prompt


def factcheck_with_perplexity(
    *,
    frage: str,
    antwort: str,
    model: str,
    max_tokens: int,
    timeout_s: int,
    sleep_s: float,
    max_retries: int,
) -> Tuple[Dict[str, Any], List[str]]:
    keys = _get_perplexity_keys()
    warnings: List[str] = []

    if not keys:
        # return a deterministic placeholder
        return (
            {
                "verdict": "maybe",
                "issues": [
                    "Perplexity API Key fehlt " "(PERPLEXITY_API_KEY oder _1/_2)."
                ],
                "suggested_sources": [],
                "optional_fix_snippet": "",
            },
            ["no_perplexity_key"],
        )

    system_prompt, user_prompt = _build_prompts(frage, antwort)

    last_err: Optional[str] = None
    attempts = 0
    while attempts < max_retries:
        attempts += 1
        for i, key in enumerate(keys):
            try:
                data = _perplexity_request(
                    api_key=key,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    timeout_s=timeout_s,
                )
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                parsed = _extract_json_obj(content)
                if parsed is None:
                    warnings.append("perplexity_non_json")
                    parsed = {
                        "verdict": "maybe",
                        "issues": [
                            "Perplexity lieferte kein parsebares JSON; "
                            "bitte manuell prüfen."
                        ],
                        "suggested_sources": [],
                        "optional_fix_snippet": "",
                    }
                # normalize fields
                verdict = str(parsed.get("verdict", "maybe")).strip().lower()
                if verdict not in {"ok", "maybe", "problem"}:
                    verdict = "maybe"
                    warnings.append("verdict_normalized")
                issues = parsed.get("issues")
                if not isinstance(issues, list):
                    issues = [str(issues)] if issues else []
                sources = parsed.get("suggested_sources")
                if not isinstance(sources, list):
                    sources = []

                result = {
                    "verdict": verdict,
                    "issues": [str(x) for x in issues if str(x).strip()],
                    "suggested_sources": [
                        {
                            "title": str(s.get("title", "")).strip(),
                            "url": str(s.get("url", "")).strip(),
                            "why": str(s.get("why", "")).strip(),
                        }
                        for s in sources
                        if isinstance(s, dict)
                    ],
                    "optional_fix_snippet": str(
                        parsed.get("optional_fix_snippet", "") or ""
                    ),
                }

                if sleep_s:
                    time.sleep(sleep_s)

                return result, warnings

            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                last_err = f"HTTPError status={status}"

                if status == 429:
                    retry_after = None
                    try:
                        ra = e.response.headers.get("Retry-After")
                        retry_after = int(ra) if ra else None
                    except Exception:
                        retry_after = None

                    # Try next key first, then backoff.
                    if i < len(keys) - 1:
                        warnings.append("perplexity_429_try_next_key")
                        continue
                    warnings.append("perplexity_429_backoff")
                    time.sleep(min(max(retry_after or 2, 1), 60))
                    continue

                if status == 401 and i < len(keys) - 1:
                    warnings.append("perplexity_401_try_next_key")
                    continue

                if status and int(status) >= 500:
                    warnings.append("perplexity_5xx_backoff")
                    time.sleep(min(2 * attempts, 10))
                    continue

                warnings.append("perplexity_http_error")
                break
            except Exception as e:
                last_err = str(e)
                warnings.append("perplexity_error")
                break

    # fallback
    return (
        {
            "verdict": "maybe",
            "issues": [
                "Perplexity-Aufruf fehlgeschlagen.",
                last_err or "unknown_error",
            ],
            "suggested_sources": [],
            "optional_fix_snippet": "",
        },
        warnings,
    )


def render_markdown_report(
    *,
    timestamp: str,
    model: str,
    seed: int,
    sample_size: int,
    warnings: List[str],
    results: List[Dict[str, Any]],
    top_n: int = 10,
) -> str:
    counts = {"ok": 0, "maybe": 0, "problem": 0}
    for r in results:
        v = r.get("verdict")
        if v in counts:
            counts[v] += 1

    def sort_key(r: Dict[str, Any]) -> Tuple[int, int]:
        v = r.get("verdict")
        sev = 0
        if v == "problem":
            sev = 2
        elif v == "maybe":
            sev = 1
        else:
            sev = 0
        # more issues first
        return (-sev, -len(r.get("issues", []) or []))

    problematic_sorted = sorted(
        [r for r in results if r.get("verdict") in {"problem", "maybe"}],
        key=sort_key,
    )

    lines: List[str] = []
    lines.append("# Perplexity Faktencheck (Stichprobe)\n")
    lines.append(f"- **Timestamp**: {timestamp}")
    lines.append(f"- **Modell**: {model}")
    lines.append(f"- **Seed**: {seed}")
    lines.append(f"- **Sample Size**: {sample_size}")
    if warnings:
        warn_text = ", ".join(sorted(set(warnings)))
        lines.append(f"- **Warnings**: {warn_text}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Verdict | Count |")
    lines.append("|---|---:|")
    lines.append(f"| ok | {counts['ok']} |")
    lines.append(f"| maybe | {counts['maybe']} |")
    lines.append(f"| problem | {counts['problem']} |")
    lines.append("")

    lines.append(f"## Top {top_n} Auffälligkeiten")
    lines.append("")

    for i, r in enumerate(problematic_sorted[:top_n], 1):
        frage = str(r.get("frage", "")).strip()
        src = str(r.get("source_file", "")).strip()
        lines.append(f"### {i}. {r.get('verdict', '').upper()} – {src}")
        lines.append("")
        frage_display = frage[:400] + ("…" if len(frage) > 400 else "")
        lines.append(f"**Frage:** {frage_display}")
        issues = r.get("issues") or []
        if issues:
            lines.append("\n**Issues:**")
            for it in issues[:10]:
                lines.append(f"- {it}")
        sources = r.get("suggested_sources") or []
        if sources:
            lines.append("\n**Empfohlene Quellen:**")
            for s in sources[:5]:
                title = s.get("title", "").strip() or "Quelle"
                url = s.get("url", "").strip()
                why = s.get("why", "").strip()
                if url:
                    lines.append(f"- {title}: `{url}` – {why}")
                else:
                    lines.append(f"- {title} – {why}")
        fix = (r.get("optional_fix_snippet") or "").strip()
        if fix:
            lines.append("\n**Optional Fix Snippet:**")
            fix_display = fix[:1200] + ("…" if len(fix) > 1200 else "")
            lines.append("\n```\n" + fix_display + "\n```\n")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Perplexity Faktencheck (Stichprobe) – schreibt Findings, " "kein Rewrite"
        )
    )
    parser.add_argument(
        "--main",
        default=str(OUTPUT_DIR / "evidenz_antworten.json"),
        help="Main Q&A JSON (wird NICHT geändert)",
    )
    parser.add_argument(
        "--problematic",
        default=str(OUTPUT_DIR / "problematic_meaningful_from_full_validation.json"),
        help="JSON mit problematischen meaningful Einträgen (erwartet ~12)",
    )
    parser.add_argument(
        "--meaningful",
        default=str(OUTPUT_DIR / "meaningful_missing.json"),
        help="JSON-Liste der meaningful Fragen (für Random-Fill)",
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--run-id",
        default="",
        help=(
            "Optionaler Run-Ident (YYYYMMDD_HHMM). "
            "Wenn leer: neu = jetzt; mit --resume: neuester Checkpoint."
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Setzt einen vorhandenen Checkpoint fort (run-id oder neuester).",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Progress-Ausgabe alle N completed Items.",
    )
    parser.add_argument(
        "--fsync-every",
        type=int,
        default=25,
        help="Checkpoint per fsync alle N neuen Items sichern (0=nie).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("PERPLEXITY_MODEL", "sonar"),
        help="Perplexity model id (default: env PERPLEXITY_MODEL or 'sonar')",
    )
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries pro Item (429/5xx) bevor Fallback 'maybe'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur Sample bauen + Output schreiben (keine API Calls)",
    )
    args = parser.parse_args()

    # Ensure .env values are visible even without python-dotenv
    _load_env_fallback(PROJECT_ROOT / ".env")

    main_path = Path(args.main)
    problematic_path = Path(args.problematic)
    meaningful_path = Path(args.meaningful)

    if not main_path.exists():
        raise SystemExit(f"Main file not found: {main_path}")
    if not problematic_path.exists():
        raise SystemExit(f"Problematic file not found: {problematic_path}")
    if not meaningful_path.exists():
        raise SystemExit(f"Meaningful file not found: {meaningful_path}")

    run_id = (args.run_id or "").strip()
    checkpoint_path: Optional[Path] = None
    if args.resume and not run_id:
        latest = _find_latest_checkpoint(OUTPUT_DIR)
        if not latest:
            raise SystemExit(
                "Kein Checkpoint gefunden. Nutze --run-id oder starte neu."
            )
        checkpoint_path = latest
        run_id = _run_id_from_checkpoint_path(latest) or run_id
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M")

    if checkpoint_path is None:
        checkpoint_path = _checkpoint_path_for_run(OUTPUT_DIR, run_id)

    out_json = OUTPUT_DIR / f"perplexity_factcheck_sample_{run_id}.json"
    out_md = OUTPUT_DIR / f"perplexity_factcheck_sample_{run_id}.md"

    main_data, main_norm_index = _load_main_index(main_path)
    problematic = _collect_problematic_questions(problematic_path)
    meaningful_questions = _collect_meaningful_questions(meaningful_path)

    sample, build_warnings = _build_sample(
        main_data=main_data,
        main_norm_index=main_norm_index,
        problematic=problematic,
        meaningful_questions=meaningful_questions,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    # Load checkpoint if present (resume) or ensure we don't overwrite
    # accidentally.
    results_by_index = _load_checkpoint_jsonl(checkpoint_path)
    if results_by_index and not args.resume and not args.dry_run:
        raise SystemExit(
            "Checkpoint existiert bereits. Nutze --resume oder wähle " "--run-id neu."
        )

    completed = len(results_by_index)
    all_warnings: List[str] = list(build_warnings)

    for n, item in enumerate(sample, 1):
        if item.index_in_evidenz in results_by_index:
            continue

        if args.dry_run:
            fc = {
                "verdict": "maybe",
                "issues": ["dry_run"],
                "suggested_sources": [],
                "optional_fix_snippet": "",
            }
            warnings = ["dry_run"]
        else:
            fc, warnings = factcheck_with_perplexity(
                frage=item.frage,
                antwort=item.antwort,
                model=args.model,
                max_tokens=args.max_tokens,
                timeout_s=args.timeout,
                sleep_s=args.sleep,
                max_retries=args.max_retries,
            )

        all_warnings.extend(warnings)

        record = {
            "index_in_evidenz_antworten": item.index_in_evidenz,
            "frage": item.frage,
            "source_file": item.source_file,
            "verdict": fc.get("verdict"),
            "issues": fc.get("issues", []),
            "suggested_sources": fc.get("suggested_sources", []),
            "optional_fix_snippet": fc.get("optional_fix_snippet", ""),
            "warnings": warnings,
            "meta": {
                "perplexity_model": args.model,
                "timestamp": run_id,
                "sample_pos": n,
            },
        }

        if not args.dry_run:
            do_fsync = args.fsync_every > 0 and (
                (completed + 1) % args.fsync_every == 0
            )
            _append_checkpoint_jsonl(
                checkpoint_path,
                record,
                fsync=do_fsync,
            )

        results_by_index[item.index_in_evidenz] = record
        completed += 1

        # Progress without leaking keys
        if completed % max(args.progress_every, 1) == 0:
            print(f"[{completed}/{len(sample)}] …", file=sys.stderr)

    # Rebuild results in sample order (stable), using checkpoint content.
    results: List[Dict[str, Any]] = []
    for pos, item in enumerate(sample, 1):
        rec = results_by_index.get(item.index_in_evidenz)
        if rec is None:
            rec = {
                "index_in_evidenz_antworten": item.index_in_evidenz,
                "frage": item.frage,
                "source_file": item.source_file,
                "verdict": "maybe",
                "issues": ["missing_result_record"],
                "suggested_sources": [],
                "optional_fix_snippet": "",
                "warnings": ["missing_result_record"],
                "meta": {
                    "perplexity_model": args.model,
                    "timestamp": run_id,
                    "sample_pos": pos,
                },
            }
        results.append(rec)

    # Merge warnings (build + per-record)
    for r in results:
        w = r.get("warnings")
        if isinstance(w, list):
            all_warnings.extend([str(x) for x in w])

    payload = {
        "timestamp": run_id,
        "model": args.model,
        "seed": args.seed,
        "sample_size": args.sample_size,
        "warnings": sorted(set(all_warnings)),
        "results": results,
        "summary": {
            "ok": sum(1 for r in results if r.get("verdict") == "ok"),
            "maybe": sum(1 for r in results if r.get("verdict") == "maybe"),
            "problem": sum(1 for r in results if r.get("verdict") == "problem"),
        },
    }

    _write_json(out_json, payload)
    md = render_markdown_report(
        timestamp=run_id,
        model=args.model,
        seed=args.seed,
        sample_size=len(results),
        warnings=payload["warnings"],
        results=results,
        top_n=10,
    )
    _write_text(out_md, md)

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    print(f"Checkpoint: {checkpoint_path}")
    print("Summary:", payload["summary"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
