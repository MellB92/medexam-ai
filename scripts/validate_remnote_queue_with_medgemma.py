#!/usr/bin/env python3
"""
Runner: MedGemma-Validierung für RemNote `needs_review` Queue.

Workflow:
1) Input-Queue (von `scripts/prepare_remnote_validation_queue.py`)
2) Optional: Minimal-RAG-Snippets aus wenigen, hochrelevanten PDFs (keyword-based)
3) MedGemma Endpoint Call (Vertex AI, chatCompletions)
4) Parse QA_VERDICT + CORRECTED_VERSION
5) Lokale Post-Validation (MedicalValidationLayer) → QA-Status finalisieren
6) Streaming Outputs + Checkpoint/Resume + Budget Gate

Input:
- `_OUTPUT/remnote_merge/remnote_needs_review_queue.jsonl`
- `_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl` (für Update-Merge)

Output:
- `_OUTPUT/remnote_merge/remnote_needs_review_medgemma_results.jsonl`
- `_OUTPUT/remnote_merge/remnote_needs_review_medgemma_report.md`
- optional: `_OUTPUT/remnote_merge/remnote_nodes_validated_medgemma.jsonl`

Hinweis:
Dieses Script überschreibt **keine** Raw `.rem` Dateien.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

import requests

try:  # pragma: no cover - optional in restricted envs
    from dotenv import find_dotenv, load_dotenv  # type: ignore

    load_dotenv(find_dotenv(usecwd=True), override=True)
except Exception:
    # Fallback: rely on process env vars
    pass


# -----------------------------
# Minimal PDF "RAG" (keyword excerpts)
# -----------------------------


def try_extract_pdf_text(pdf_path: Path, max_chars: int = 120_000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""

    try:
        reader = PdfReader(str(pdf_path))
        out: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
                if t.strip():
                    out.append(t)
                if sum(len(x) for x in out) >= max_chars:
                    break
            except Exception:
                continue
        return "\n\n".join(out)
    except Exception:
        return ""


def get_pdf_text_cached(cache_dir: Path, pdf_path: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{pdf_path.stem}.txt"
    try:
        if cache_file.exists() and cache_file.stat().st_size > 50_000:
            return cache_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

    text = try_extract_pdf_text(pdf_path)
    try:
        if text.strip():
            cache_file.write_text(text, encoding="utf-8")
    except Exception:
        pass
    return text


def find_pdf_by_name_hint(base_dir: Path, hints: list[str]) -> list[Path]:
    """
    Sucht PDFs in `_BIBLIOTHEK/Leitlinien/**` anhand von Namens-Hints.
    (Robuster als Hardcoding eines festen Pfads.)
    """
    if not base_dir.exists():
        return []
    pdfs = list(base_dir.rglob("*.pdf"))
    scored: list[tuple[int, Path]] = []
    for p in pdfs:
        name = p.name.lower()
        score = 0
        for h in hints:
            if h.lower() in name:
                score += 10
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [p for _, p in scored[:5]]


def build_rag_snippets(repo_root: Path, category: str, text: str, max_snippets: int = 4) -> str:
    leit = repo_root / "_BIBLIOTHEK" / "Leitlinien"
    sources: list[Path] = []
    if category == "strahlenschutz":
        sources = find_pdf_by_name_hint(leit, ["strlschv", "strahlenschutz", "strahlenschutzverordnung", "strl sch v"])
    elif category == "pharmakologie":
        sources = find_pdf_by_name_hint(leit, ["btmvv", "betäubungsmittel", "betaeubungsmittel"])
    elif category == "rechtsmedizin":
        sources = find_pdf_by_name_hint(leit, ["heilberg", "berufsordnung", "muster-berufsordnung", "heilberuf"])

    if not sources:
        return ""

    keywords = [k for k in re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", text)][:25]
    cache_dir = repo_root / "_OUTPUT" / "validation_rag_cache"
    snippets: list[str] = []

    for src in sources:
        full = get_pdf_text_cached(cache_dir, src)
        if not full.strip():
            continue
        full_l = full.lower()
        for kw in keywords:
            kw_l = kw.lower()
            pos = full_l.find(kw_l)
            if pos == -1:
                continue
            start = max(0, pos - 400)
            end = min(len(full), pos + 400)
            excerpt = full[start:end].strip()
            if excerpt and excerpt not in snippets:
                snippets.append(f"### Quelle: {src.name}\n\n{excerpt}\n")
            if len(snippets) >= max_snippets:
                break
        if len(snippets) >= max_snippets:
            break

    return "\n\n".join(snippets)


# -----------------------------
# MedGemma Client (Endpoint)
# -----------------------------


class MedGemmaClient:
    def __init__(self, project: str, region: str, endpoint_id: str, access_token: Optional[str] = None) -> None:
        self.project = project
        self.region = region
        self.endpoint_id = endpoint_id
        self._access_token = (access_token or "").strip() or None
        self._shared_host = f"{self.region}-aiplatform.googleapis.com"
        self._prediction_domain = (os.getenv("MEDGEMMA_PREDICTION_DOMAIN") or "").strip() or None

    def _build_predict_url(self, host: str) -> str:
        return f"https://{host}/v1/projects/{self.project}/locations/{self.region}/endpoints/{self.endpoint_id}:predict"

    @staticmethod
    def _extract_dedicated_domain(error_payload: Any) -> Optional[str]:
        try:
            msg = ""
            if isinstance(error_payload, dict):
                err = error_payload.get("error") or {}
                if isinstance(err, dict):
                    msg = str(err.get("message") or "")
                else:
                    msg = str(error_payload)
            else:
                msg = str(error_payload)

            m = re.search(r"dedicated domain name '([^']+)'", msg)
            if m:
                return m.group(1).strip()
        except Exception:
            return None
        return None

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        tok = os.getenv("GOOGLE_ACCESS_TOKEN")
        if tok and tok.strip():
            return tok.strip()

        def run(cmd: list[str]) -> str:
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if p.returncode != 0:
                raise RuntimeError((p.stderr or p.stdout or "").strip() or f"Command failed: {' '.join(cmd)}")
            out = (p.stdout or "").strip()
            if not out:
                raise RuntimeError(f"Empty token from: {' '.join(cmd)}")
            return out

        errors: list[str] = []
        for cmd in (
            ["gcloud", "auth", "application-default", "print-access-token"],
            ["gcloud", "auth", "print-access-token"],
        ):
            try:
                return run(cmd)
            except Exception as e:
                errors.append(f"{' '.join(cmd)} -> {e}")

        raise RuntimeError(
            "Kein Google Access Token verfügbar. Setze `GOOGLE_ACCESS_TOKEN` oder nutze `--access-token`, "
            "oder re-authentifiziere gcloud (interaktiv): `gcloud auth login` + `gcloud auth application-default login`. "
            f"Details: {errors}"
        )

    def chat(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Dict[str, Any]:
        request = {
            "@requestFormat": "chatCompletions",
            "messages": [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ],
            "max_tokens": int(max_tokens),
        }
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {"instances": [request]}
        primary_host = self._prediction_domain or self._shared_host
        url = self._build_predict_url(primary_host)
        r = requests.post(url, headers=headers, json=body, timeout=120)

        if r.status_code == 400:
            try:
                payload = r.json()
            except Exception:
                payload = {"raw": r.text}
            dom = self._extract_dedicated_domain(payload)
            if dom and dom != self._prediction_domain:
                self._prediction_domain = dom
                url2 = self._build_predict_url(dom)
                r = requests.post(url2, headers=headers, json=body, timeout=120)

        if not r.ok:
            raise RuntimeError(f"MedGemma HTTP {r.status_code}: {r.text[:2000]}")

        data = r.json()
        preds = data.get("predictions")
        pred0: Dict[str, Any] = {}
        if isinstance(preds, list) and preds:
            if isinstance(preds[0], dict):
                pred0 = preds[0]
        elif isinstance(preds, dict):
            pred0 = preds

        payload: Dict[str, Any] = {"raw": pred0, "text": "", "usage": {}}
        choices = (pred0.get("choices", []) or []) if isinstance(pred0, dict) else []
        if choices:
            payload["text"] = choices[0].get("message", {}).get("content", "") or ""
        payload["usage"] = pred0.get("usage", {}) or {}
        return payload


def parse_medgemma_output(text: str) -> Dict[str, Any]:
    verdict = None
    m = re.search(r"QA_VERDICT\s*:\s*(VERIFIED|NEEDS_REVIEW)", text or "", re.IGNORECASE)
    if m:
        verdict_raw = m.group(1).lower()
        verdict = "verified" if verdict_raw == "verified" else "needs_review"

    corrected = None
    m2 = re.search(r"CORRECTED_VERSION\s*:\s*(.*)", text or "", re.IGNORECASE | re.DOTALL)
    if m2:
        corrected = m2.group(1).strip()
        if corrected.lower() == "unchanged":
            corrected = None

    return {"qa_verdict": verdict, "corrected_text": corrected}


# -----------------------------
# Local validator (post-check)
# -----------------------------


def run_local_validation(text: str) -> Dict[str, Any]:
    try:
        # Import direkt aus Datei (ohne `import core` side-effects)
        import importlib.util

        repo_root = Path(__file__).parent.parent
        mv_path = (repo_root / "core" / "medical_validator.py").resolve()
        spec = importlib.util.spec_from_file_location("_medical_validator_local", mv_path)
        if not spec or not spec.loader:
            return {"available": False, "error": "spec_loader_missing"}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        MedicalValidationLayer = getattr(module, "MedicalValidationLayer")
        validator = MedicalValidationLayer()
        res = validator.validate(text, source_file="remnote")
        meta = {
            "is_valid": bool(getattr(res, "is_valid", False)),
            "confidence": float(getattr(res, "confidence_score", 0.0) or 0.0),
            "issues_count": len(getattr(res, "issues", []) or []),
            "warnings_count": len(getattr(res, "warnings", []) or []),
        }
        return {"available": True, "meta": meta}
    except Exception as e:
        return {"available": False, "error": str(e)}


# -----------------------------
# IO helpers
# -----------------------------


def load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def load_checkpoint(path: Path) -> Set[str]:
    try:
        if not path.exists():
            return set()
        data = json.loads(path.read_text(encoding="utf-8"))
        done = data.get("done_node_ids") or []
        if isinstance(done, list):
            return set(str(x) for x in done)
    except Exception:
        pass
    return set()


def write_checkpoint(path: Path, done: Set[str], meta: Dict[str, Any]) -> None:
    payload = {"done_node_ids": sorted(done), **meta}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# -----------------------------
# Main
# -----------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-queue", default="_OUTPUT/remnote_merge/remnote_needs_review_queue.jsonl")
    parser.add_argument("--validated-nodes", default="_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl")
    parser.add_argument("--output-results", default="_OUTPUT/remnote_merge/remnote_needs_review_medgemma_results.jsonl")
    parser.add_argument("--output-report", default="_OUTPUT/remnote_merge/remnote_needs_review_medgemma_report.md")
    parser.add_argument(
        "--output-updated-nodes", default="_OUTPUT/remnote_merge/remnote_nodes_validated_medgemma.jsonl"
    )
    parser.add_argument("--write-updated-nodes", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint", default="_OUTPUT/remnote_merge/remnote_needs_review_medgemma_checkpoint.json")
    parser.add_argument("--max-items", type=int, default=0, help="0 = alle")
    parser.add_argument("--budget-eur", type=float, default=5.0)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument(
        "--access-token",
        default="",
        help="Optional: Google OAuth Access Token (überschreibt gcloud). Alternative: env GOOGLE_ACCESS_TOKEN.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    queue_path = repo_root / args.input_queue
    nodes_path = repo_root / args.validated_nodes
    out_results = repo_root / args.output_results
    out_report = repo_root / args.output_report
    out_nodes = repo_root / args.output_updated_nodes
    checkpoint_path = repo_root / args.checkpoint

    queue = load_jsonl(queue_path)
    if args.max_items and args.max_items > 0:
        queue = queue[: args.max_items]

    done: Set[str] = set()
    if args.resume:
        done = load_checkpoint(checkpoint_path)

    # Prepare MedGemma client (unless dry-run)
    medgemma_client: Optional[MedGemmaClient] = None
    if not args.dry_run:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "medexamenai")
        region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        endpoint_id = os.getenv("MEDGEMMA_ENDPOINT_ID")
        if not endpoint_id:
            raise SystemExit("❌ MEDGEMMA_ENDPOINT_ID fehlt (env).")
        medgemma_client = MedGemmaClient(
            project=project,
            region=region,
            endpoint_id=endpoint_id,
            access_token=(args.access_token or None),
        )
        # Token-Check upfront (Fail-fast)
        _ = medgemma_client._get_access_token()

    # Budget (very rough)
    EUR_USD_RATE = 1.05
    COST_PER_1K_INPUT_USD = 0.0001
    COST_PER_1K_OUTPUT_USD = 0.0004
    budget_usd = float(args.budget_eur) * EUR_USD_RATE
    spent_usd = 0.0

    # Streaming output
    out_results.parent.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        safe_backup_existing(out_results)

    status_counts = Counter()
    cat_counts = Counter()
    risk_counts = Counter()
    medgemma_calls_attempted = 0
    medgemma_calls_succeeded = 0
    medgemma_errors = Counter()
    processed = 0
    skipped = 0

    with open(out_results, "a", encoding="utf-8") as f_out:
        for item in queue:
            node_id = str(item.get("node_id") or "")
            if not node_id:
                continue
            if node_id in done:
                skipped += 1
                continue

            category = str(item.get("category") or "rest")
            risk_flags = item.get("risk_flags") or []
            cat_counts[category] += 1
            for rf in risk_flags:
                risk_counts[str(rf)] += 1

            text = (item.get("text") or "").strip()
            rag = (
                build_rag_snippets(repo_root, category, text)
                if category in {"strahlenschutz", "pharmakologie", "rechtsmedizin"}
                else ""
            )

            system_prompt = "Du bist Prüfer für die deutsche ärztliche Kenntnisprüfung Münster. Antworte direkt."
            user_prompt = (item.get("medgemma_prompt") or "").strip()
            if rag.strip():
                user_prompt = user_prompt + "\n\nRAG_AUSZUEGE:\n" + rag

            if args.dry_run:
                result = {
                    "node_id": node_id,
                    "category": category,
                    "risk_flags": risk_flags,
                    "qa_status": "unverified",
                    "dry_run": True,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
                done.add(node_id)
                processed += 1
                continue

            assert medgemma_client is not None

            # Budget gate (estimate)
            est_in = int((len(system_prompt) + len(user_prompt)) / 4)
            est_out = int(args.max_tokens)
            est_cost = (est_in / 1000) * COST_PER_1K_INPUT_USD + (est_out / 1000) * COST_PER_1K_OUTPUT_USD
            if spent_usd + est_cost > budget_usd:
                result = {
                    "node_id": node_id,
                    "category": category,
                    "risk_flags": risk_flags,
                    "qa_status": "unverified",
                    "skipped_reason": "budget_exhausted_estimate",
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
                done.add(node_id)
                skipped += 1
                write_checkpoint(
                    checkpoint_path, done, {"spent_usd": spent_usd, "processed": processed, "skipped": skipped}
                )
                continue

            try:
                medgemma_calls_attempted += 1
                payload = medgemma_client.chat(
                    system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=int(args.max_tokens)
                )
                usage = payload.get("usage", {}) or {}
                in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or est_in)
                out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or est_out)
                real_cost = (in_tok / 1000) * COST_PER_1K_INPUT_USD + (out_tok / 1000) * COST_PER_1K_OUTPUT_USD
                spent_usd += float(real_cost)

                parsed = parse_medgemma_output(payload.get("text", ""))
                qa_status = parsed.get("qa_verdict") or "needs_review"
                medgemma_calls_succeeded += 1

                corrected = parsed.get("corrected_text") or None
                final_text = corrected.strip() if isinstance(corrected, str) and corrected.strip() else text

                post = run_local_validation(final_text) if final_text else {"available": False}
                # Conservative: if local validator says invalid/low confidence, force needs_review
                if post.get("available"):
                    meta = post.get("meta") or {}
                    try:
                        if (not bool(meta.get("is_valid"))) or float(meta.get("confidence") or 0.0) < 0.65:
                            qa_status = "needs_review"
                    except Exception:
                        qa_status = "needs_review"

                result = {
                    "node_id": node_id,
                    "category": category,
                    "risk_flags": risk_flags,
                    "qa_status": qa_status,
                    "validated_text": final_text,
                    "medgemma": {
                        "usage": usage,
                        "response_preview": (payload.get("text", "") or "")[:2000],
                    },
                    "local_post_validation": post,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            except Exception as e:
                result = {
                    "node_id": node_id,
                    "category": category,
                    "risk_flags": risk_flags,
                    "qa_status": "needs_review",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                medgemma_errors[str(e).splitlines()[0][:120]] += 1

            status_counts[result.get("qa_status") or "unknown"] += 1
            f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
            done.add(node_id)
            processed += 1

            # checkpoint every N
            if processed % 5 == 0:
                write_checkpoint(
                    checkpoint_path,
                    done,
                    {
                        "spent_usd": spent_usd,
                        "spent_eur_est": round(spent_usd / EUR_USD_RATE, 4),
                        "processed": processed,
                        "skipped": skipped,
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )

            # small delay to be gentle
            time.sleep(0.2)

    # Final checkpoint
    write_checkpoint(
        checkpoint_path,
        done,
        {
            "spent_usd": spent_usd,
            "spent_eur_est": round(spent_usd / EUR_USD_RATE, 4),
            "processed": processed,
            "skipped": skipped,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        },
    )

    # Optionally merge updates back into nodes file (write new file)
    updated_nodes_written = False
    if args.write_updated_nodes:
        base_nodes = load_jsonl(nodes_path)
        # Build update map from results file (last write wins)
        updates: Dict[str, Dict[str, Any]] = {}
        for r in load_jsonl(out_results):
            nid = str(r.get("node_id") or "")
            if nid:
                updates[nid] = r

        merged: list[dict] = []
        for n in base_nodes:
            nid = str(n.get("node_id") or "")
            if nid and nid in updates:
                r = updates[nid]
                n["qa_status"] = r.get("qa_status") or n.get("qa_status") or "unverified"
                if r.get("validated_text"):
                    n["validated_text"] = r.get("validated_text")
                n["medgemma_validation"] = r.get("medgemma") or {}
                n["local_post_validation"] = r.get("local_post_validation") or {}
                n["qa_updated_at"] = r.get("timestamp")
            merged.append(n)

        safe_backup_existing(out_nodes)
        with open(out_nodes, "w", encoding="utf-8") as f:
            for n in merged:
                f.write(json.dumps(n, ensure_ascii=False) + "\n")
        updated_nodes_written = True

    # Report
    out_report.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# RemNote MedGemma Runner Report\n\n")
    lines.append(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append(f"- input_queue: `{args.input_queue}`\n")
    lines.append(f"- output_results: `{args.output_results}`\n")
    lines.append(f"- resume: {bool(args.resume)}\n")
    lines.append(f"- dry_run: {bool(args.dry_run)}\n")
    lines.append(f"- budget_eur: {args.budget_eur}\n")
    lines.append(f"- spent_eur_est: {round(spent_usd / EUR_USD_RATE, 4)}\n")
    lines.append(f"- processed: {processed}\n")
    lines.append(f"- skipped: {skipped}\n")
    lines.append(f"- medgemma_calls_attempted: {medgemma_calls_attempted}\n")
    lines.append(f"- medgemma_calls_succeeded: {medgemma_calls_succeeded}\n")
    if args.write_updated_nodes:
        lines.append(f"- updated_nodes_written: {updated_nodes_written}\n")
        lines.append(f"- output_updated_nodes: `{args.output_updated_nodes}`\n")

    # Overall summary across the full results file (useful when --resume splits runs)
    try:
        all_results = load_jsonl(out_results)
    except Exception:
        all_results = []

    if all_results:
        overall_status = Counter()
        overall_cat = Counter()
        overall_risk = Counter()
        overall_errors = 0
        for r in all_results:
            overall_status[str(r.get("qa_status") or "unknown")] += 1
            overall_cat[str(r.get("category") or "rest")] += 1
            for rf in r.get("risk_flags") or []:
                overall_risk[str(rf)] += 1
            if r.get("error"):
                overall_errors += 1

        lines.append("\n## Gesamt (alle Results)\n\n")
        lines.append(f"- total_results: {len(all_results)}\n")
        lines.append(f"- total_errors: {overall_errors}\n")

        lines.append("\n### QA Status (gesamt)\n\n")
        for k in ["verified", "needs_review", "unverified", "unknown"]:
            if overall_status.get(k):
                lines.append(f"- **{k}**: {overall_status[k]}\n")

        lines.append("\n### Kategorien (gesamt)\n\n")
        for k, v in overall_cat.most_common():
            lines.append(f"- **{k}**: {v}\n")

        if overall_risk:
            lines.append("\n### Risk Flags (gesamt, Top 10)\n\n")
            for k, v in overall_risk.most_common(10):
                lines.append(f"- **{k}**: {v}\n")

    lines.append("\n## Kategorien\n\n")
    for k in ["strahlenschutz", "pharmakologie", "rechtsmedizin", "rest"]:
        if cat_counts.get(k):
            lines.append(f"- **{k}**: {cat_counts[k]}\n")

    lines.append("\n## QA Status\n\n")
    for k in ["verified", "needs_review", "unverified"]:
        if status_counts.get(k):
            lines.append(f"- **{k}**: {status_counts[k]}\n")

    lines.append("\n## Risk Flags (Top)\n\n")
    for k, v in risk_counts.most_common(10):
        lines.append(f"- **{k}**: {v}\n")

    if medgemma_errors:
        lines.append("\n## MedGemma Fehler (Top 5)\n\n")
        for msg, cnt in medgemma_errors.most_common(5):
            lines.append(f"- **{cnt}×** `{msg}`\n")

    lines.append("\n---\n")
    lines.append("## Run Commands\n\n")
    lines.append("```bash\n")
    lines.append(f"cd {repo_root}\n")
    lines.append(
        "python3 scripts/validate_remnote_queue_with_medgemma.py --budget-eur 5.0 --resume --write-updated-nodes\n"
    )
    lines.append("# Optional: falls gcloud nicht non-interaktiv refreshen kann:\n")
    lines.append("#   export GOOGLE_ACCESS_TOKEN='...'\n")
    lines.append("#   oder: --access-token '...'\n")
    lines.append("```\n")

    out_report.write_text("".join(lines), encoding="utf-8")

    print(f"✅ results: {out_results} (processed={processed}, skipped={skipped})")
    print(f"✅ report:  {out_report}")
    if args.write_updated_nodes:
        print(f"✅ updated_nodes: {out_nodes}")


if __name__ == "__main__":
    main()
