#!/usr/bin/env python3
"""
Aufgabe 1: Validierungs-Workflow für reparierte Karten

Input:
- _OUTPUT/batch_repair_input.jsonl   (Pipeline v2: context repair + match_confidence)

Output:
- _OUTPUT/validation_report.md

Optional (wenn --write-updated-batch):
- schreibt qa_status + validation_meta zurück in batch_repair_input.jsonl

Validierungs-Philosophie (Projektstandard):
- Ohne externe Calls: nur lokale Pre-Validatoren + Priorisierung (keine "qa::verified" Halluzination)
- Mit --use-medgemma: MedGemma liefert QA_VERDICT + FINAL_ANSWER, anschließend lokale Checks
  → qa_status = verified | needs_review

Wichtig:
Dieses Script ist absichtlich konservativ. "verified" wird nur gesetzt, wenn die
MedGemma-Validierung aktiv ist UND keine kritischen lokalen Issues gefunden werden.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    # Optional: in der Cursor-Sandbox kann `.env` ggf. nicht lesbar sein (ignored file).
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    # Fallback: nutze nur echte Prozess-Envvars
    pass


# -----------------------------
# Kategorie-/Prioritätslogik
# -----------------------------


CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "strahlenschutz",
        re.compile(
            r"(strahlenschutz|strlschv|euratom|alara|dosisgrenz|mSv|sievert|dosimeter|dosimetrie|"
            r"kontrollbereich|sperrbereich|fachkunde|sachkunde|"
            r"röntgen.*(anfordern|anforderung|fachkunde|sachkunde)|ionisierend)",
            re.IGNORECASE,
        ),
    ),
    (
        "pharmakologie",
        re.compile(
            r"(dosierung|dosis|mg\b|µg|ug\b|iu\b|ie\b|btm|btmvv|opioid|antibiotik|uaw|nebenwirkung|"
            r"rivaroxaban|xarelto|apixaban|eliquis|heparin|insulin|metformin|morphin|propofol)",
            re.IGNORECASE,
        ),
    ),
    (
        "rechtsmedizin",
        re.compile(
            r"(rechtsmedizin|leichenschau|todes(zeichen|art|ursache)?|obduktion|todesbescheinigung|"
            r"heilberg|berufsordnung|§\s*\d+|bgb|stgb|ifsg|meldepflicht)",
            re.IGNORECASE,
        ),
    ),
]


def classify_category(text: str) -> str:
    for name, rx in CATEGORY_RULES:
        if rx.search(text or ""):
            return name
    return "rest"


def build_category_blob(item: Dict[str, Any]) -> str:
    """
    Baut einen Text für Kategorie-/Prioritätsklassifikation.

    Wichtig (Projektstandard):
    - NICHT `original_antwort` verwenden (oft lang/unspezifisch/contaminiert).
    - Bei Template-Karten NICHT `repaired_answer` verwenden (enthält häufig generische Boilerplate
      + evtl. irrelevante Preview-Snippets und würde Kategorien verzerren).
    - Stattdessen: Frage + (bei fallbasierten Karten) extrahierter Kontext (Dx/DD/Medikation etc.).
    """
    parts: list[str] = []
    frage = (item.get("original_frage", "") or "").strip()
    if frage:
        parts.append(frage)

    # Nur bei echten Fallkarten: Kontextfelder als Signal nutzen
    if (item.get("repair_status") or "").strip().lower() == "repaired":
        ctx = item.get("extracted_context", {}) or {}
        if isinstance(ctx, dict):
            dx = ctx.get("diagnose")
            if isinstance(dx, str) and dx.strip():
                parts.append(dx.strip())
            dd = ctx.get("differentialdiagnosen") or []
            if isinstance(dd, list):
                parts.extend([str(x) for x in dd[:8] if str(x).strip()])
            meds = ctx.get("medikation") or []
            if isinstance(meds, list):
                parts.extend([str(x) for x in meds[:8] if str(x).strip()])
            bef = ctx.get("befunde") or {}
            if isinstance(bef, dict):
                for k in ("bildgebung", "labor"):
                    v = bef.get(k) or []
                    if isinstance(v, list):
                        parts.extend([str(x) for x in v[:5] if str(x).strip()])

    return "\n".join(parts).strip()


def priority_rank(category: str) -> int:
    # user-specified order: Strahlenschutz → Pharmako → Rechtsmedizin → Rest
    if category == "strahlenschutz":
        return 0
    if category == "pharmakologie":
        return 1
    if category == "rechtsmedizin":
        return 2
    return 3


# -----------------------------
# Lokale Validatoren
# -----------------------------


def run_local_validation(query: str, answer: str, question_id: str) -> Dict[str, Any]:
    """
    Nutzt die bereits vorhandene EnhancedValidationPipeline (lokal, keine API).
    """
    try:
        from core.enhanced_validation_pipeline import EnhancedValidationPipeline  # type: ignore

        pipeline = EnhancedValidationPipeline(strict_mode=False)
        final_answer, meta = pipeline.validate_answer(answer=answer, query=query, question_id=question_id)
        return {
            "available": True,
            "final_answer": final_answer,
            "meta": meta,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }


# -----------------------------
# MedGemma Endpoint (optional)
# -----------------------------


class MedGemmaClient:
    """
    Leichter Client über Vertex REST API (vermeidet schwere SDK-Imports).

    Auth:
    - nutzt `GOOGLE_ACCESS_TOKEN` falls gesetzt, sonst
    - `gcloud auth application-default print-access-token`, fallback
    - `gcloud auth print-access-token`
    """

    def __init__(self, project: str, region: str, endpoint_id: str, access_token: Optional[str] = None) -> None:
        self.project = project
        self.region = region
        self.endpoint_id = endpoint_id
        self._access_token = (access_token or "").strip() or None
        # Shared Vertex domain (funktioniert NICHT für dedicated endpoints)
        self._shared_host = f"{self.region}-aiplatform.googleapis.com"
        # Optional: dedicated prediction domain (wird auto-detektiert oder kann per env gesetzt werden)
        self._prediction_domain = (os.getenv("MEDGEMMA_PREDICTION_DOMAIN") or "").strip() or None

    def _build_predict_url(self, host: str) -> str:
        return f"https://{host}/v1/projects/{self.project}/locations/{self.region}/endpoints/{self.endpoint_id}:predict"

    @staticmethod
    def _extract_dedicated_domain(error_payload: Any) -> Optional[str]:
        """
        Vertex gibt bei dedicated endpoints typischerweise:
          error.message: "... dedicated domain name 'XYZ.prediction.vertexai.goog'"
        """
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
        # 1) Prefer dedicated domain if known
        primary_host = self._prediction_domain or self._shared_host
        url = self._build_predict_url(primary_host)
        r = requests.post(url, headers=headers, json=body, timeout=120)

        # 2) Auto-detect dedicated domain requirement and retry once
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
            # Include response body for debuggability (keine Secrets enthalten)
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
    """
    Erwartetes Format (durch Prompt erzwungen):
      QA_VERDICT: VERIFIED|NEEDS_REVIEW
      FINAL_ANSWER:
      ...
    """
    verdict = None
    m = re.search(r"QA_VERDICT\s*:\s*(VERIFIED|NEEDS_REVIEW)", text or "", re.IGNORECASE)
    if m:
        verdict = m.group(1).lower()
        verdict = "verified" if verdict == "verified" else "needs_review"

    final_answer = None
    m2 = re.search(r"FINAL_ANSWER\s*:\s*(.*)", text or "", re.IGNORECASE | re.DOTALL)
    if m2:
        final_answer = m2.group(1).strip()

    return {
        "qa_verdict": verdict,
        "final_answer": final_answer,
    }


# -----------------------------
# Prompt Templates
# -----------------------------


def build_system_prompt(category: str) -> str:
    base = (
        "Du bist Prüfer für die deutsche ärztliche Kenntnisprüfung Münster.\n\n"
        "WICHTIG:\n"
        "- Antworte direkt und strukturiert.\n"
        "- Wenn Zahlen/Dosierungen/Paragraphen vorkommen: nenne sie exakt.\n"
        "- Nutze ausschließlich den gegebenen Kontext (Fallkontext + RAG-Auszüge). Keine freien Behauptungen.\n\n"
        "Output-Format (exakt so):\n"
        "QA_VERDICT: VERIFIED oder NEEDS_REVIEW\n"
        "FINAL_ANSWER:\n"
        "[deine finale Antwort]\n"
    )
    if category == "strahlenschutz":
        return base + "\nFokus: Strahlenschutz (Dosisgrenzen, ALARA, Schwangerschaft, Dokumentation)."
    if category == "pharmakologie":
        return base + "\nFokus: Pharmakologie (Dosierungen, Kontraindikationen, UAW, BTM-Basics)."
    if category == "rechtsmedizin":
        return base + "\nFokus: Rechtsmedizin/Recht (Paragraphen, Fristen, Vorgehen, Dokumentation)."
    return base + "\nFokus: klinische Prüfung – sichere, knappe Antwort."


def build_user_prompt(item: Dict[str, Any], rag_snippets: str) -> str:
    frage = item.get("original_frage", "")
    answer = item.get("repaired_answer", "") or item.get("original_antwort", "")
    context = item.get("extracted_context", {}) or {}
    return (
        f"ORIGINAL_FRAGE:\n{frage}\n\n"
        f"AKTUELLE_ANTWORT (unverified):\n{answer}\n\n"
        f"EXTRAHIERTER_FALLKONTEXT (strukturiert):\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        f"RAG_AUSZUEGE:\n{rag_snippets.strip() if rag_snippets.strip() else '[keine]'}\n\n"
        "Aufgabe:\n"
        "1) Prüfe, ob die Antwort inhaltlich korrekt zum Kontext passt.\n"
        "2) Ergänze fehlende kritische Details (z.B. Grenzwerte/Dosis/§) NUR wenn sie in RAG_AUSZUEGE stehen.\n"
        "3) Setze QA_VERDICT:\n"
        "   - VERIFIED: wenn konsistent + keine kritischen Fakten fehlen\n"
        "   - NEEDS_REVIEW: wenn Kontext nicht reicht / Unsicherheit / kritische Fakten fehlen\n"
    )


# -----------------------------
# RAG-lite (PDF-Textauszug)
# -----------------------------


def try_extract_pdf_text(pdf_path: Path, max_chars: int = 250_000) -> str:
    """
    Sehr einfache PDF-Text-Extraktion (ohne Embeddings), nur für RAG-AUSZUEGE.
    """
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
    """
    Cached PDF extraction (um nicht pro Karte denselben PDF-Text neu zu extrahieren).
    """
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


def find_pdf_by_name_hint(base_dir: Path, hints: list[str], limit: int = 5) -> list[Path]:
    """
    Sucht PDFs rekursiv in `_BIBLIOTHEK/Leitlinien/**` anhand von Namens-Hints.
    Robuster als ein harter Pfad, wenn Dateien verschoben/umbenannt wurden.
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
    return [p for _, p in scored[:limit]]


def build_rag_snippets_for_item(repo_root: Path, category: str, item: Dict[str, Any], max_snippets: int = 4) -> str:
    """
    Minimaler RAG: wir ziehen nur aus wenigen, hochrelevanten PDFs Auszüge.
    """
    sources: list[Path] = []
    leit = repo_root / "_BIBLIOTHEK" / "Leitlinien"
    if category == "strahlenschutz":
        sources = find_pdf_by_name_hint(leit, ["strlschv", "strahlenschutz", "strahlenschutzverordnung", "strl sch v"])
    elif category == "pharmakologie":
        sources = find_pdf_by_name_hint(leit, ["btmvv", "betäubungsmittel", "betaeubungsmittel"])
    elif category == "rechtsmedizin":
        sources = find_pdf_by_name_hint(leit, ["heilberg", "berufsordnung", "muster-berufsordnung", "heilberuf"])

    q_text = build_category_blob(item) or (item.get("original_frage", "") or "")
    keywords = [k for k in re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", q_text)][:25]

    cache_dir = repo_root / "_OUTPUT" / "validation_rag_cache"
    snippets: list[str] = []
    for src in sources:
        if not src.exists():
            continue
        full = get_pdf_text_cached(cache_dir, src)
        if not full.strip():
            continue
        full_l = full.lower()
        found = 0
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
                found += 1
            if len(snippets) >= max_snippets:
                break
        if len(snippets) >= max_snippets:
            break

    return "\n\n".join(snippets)


# -----------------------------
# Main Workflow
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


def write_jsonl(path: Path, items: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="_OUTPUT/batch_repair_input.jsonl")
    parser.add_argument("--output-report", default="_OUTPUT/validation_report.md")
    parser.add_argument("--write-updated-batch", action="store_true")
    parser.add_argument("--use-medgemma", action="store_true", help="führt echte MedGemma-Validierung aus (Vertex).")
    parser.add_argument(
        "--access-token",
        default="",
        help="Optional: Google OAuth Access Token (überschreibt gcloud). Alternative: env GOOGLE_ACCESS_TOKEN.",
    )
    parser.add_argument(
        "--only-repaired",
        action="store_true",
        help="nur fallbasierte Karten (`repair_status == repaired`) validieren; Templates werden ignoriert",
    )
    parser.add_argument(
        "--skip-templates",
        action="store_true",
        help="überspringt Template-Karten (repair_status==template) komplett (Default: Templates werden mitvalidiert)",
    )
    parser.add_argument("--max-items", type=int, default=0, help="0 = alle")
    parser.add_argument("--budget-eur", type=float, default=5.0)
    parser.add_argument("--max-tokens", type=int, default=800)
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    in_path = repo_root / args.input
    out_report = repo_root / args.output_report

    items = load_jsonl(in_path)

    # Filter: medgemma_relevant + qa::unverified
    to_validate: list[dict] = []
    for it in items:
        qa_status = it.get("qa_status") or "unverified"
        it["qa_status"] = qa_status
        if bool(it.get("medgemma_relevant")) and qa_status == "unverified":
            if args.only_repaired and (it.get("repair_status") or "").strip().lower() != "repaired":
                continue
            if args.skip_templates and (it.get("repair_status") or "").strip().lower() == "template":
                continue
            to_validate.append(it)

    # kategorisieren & sortieren
    enriched: list[dict] = []
    for it in to_validate:
        # Kategorie-Scoping: nur stabile Signale (Frage + Kontextfelder).
        # Verhindert, dass Template-Boilerplate/Preview die Kategorie verfälscht.
        blob = build_category_blob(it)
        cat = classify_category(blob)
        it["_validation_category"] = cat
        it["_validation_category_blob_preview"] = blob[:500]
        enriched.append(it)

    enriched.sort(
        key=lambda x: (
            priority_rank(x["_validation_category"]),
            0 if (str(x.get("repair_status") or "").strip().lower() == "repaired") else 1,
            # Rest nach match_confidence (niedrige zuerst = risk-first)
            float(x.get("match_confidence", 0.0) or 0.0) if x["_validation_category"] == "rest" else 0.0,
            int(x.get("original_index", 0) or 0),
        )
    )

    if args.max_items and args.max_items > 0:
        enriched = enriched[: args.max_items]

    # Optional: MedGemma initialisieren
    medgemma_client: Optional[MedGemmaClient] = None
    medgemma_ready = False
    medgemma_err = None
    if args.use_medgemma:
        try:
            project = os.getenv("GOOGLE_CLOUD_PROJECT", "medexamenai")
            region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
            endpoint_id = os.getenv("MEDGEMMA_ENDPOINT_ID")
            if not endpoint_id:
                raise RuntimeError("MEDGEMMA_ENDPOINT_ID fehlt (env).")
            medgemma_client = MedGemmaClient(
                project=project,
                region=region,
                endpoint_id=endpoint_id,
                access_token=(args.access_token or None),
            )
            # Token-Check upfront (Fail-fast mit klarer Fehlermeldung)
            _ = medgemma_client._get_access_token()
            medgemma_ready = True
        except Exception as e:
            medgemma_err = str(e)
            medgemma_ready = False

        if not medgemma_ready:
            raise SystemExit(f"❌ --use-medgemma aktiviert, aber MedGemma ist nicht bereit: {medgemma_err}")

    # Budget tracking (sehr grobe Heuristik, echte Usage wird bevorzugt wenn vorhanden)
    EUR_USD_RATE = 1.05
    COST_PER_1K_INPUT_USD = 0.0001
    COST_PER_1K_OUTPUT_USD = 0.0004
    budget_usd = float(args.budget_eur) * EUR_USD_RATE
    spent_usd = 0.0

    # Validierung
    results: list[dict] = []
    status_counts = Counter()
    cat_counts = Counter()
    medgemma_calls_attempted = 0
    medgemma_calls_succeeded = 0
    medgemma_errors = Counter()

    for it in enriched:
        qid = it.get("id") or f"repair_{it.get('original_index', 0):05d}"
        cat = it.get("_validation_category", "rest")
        cat_counts[cat] += 1

        frage = it.get("original_frage", "") or ""
        answer = it.get("repaired_answer", "") or it.get("original_antwort", "")
        query = frage  # minimal; Kontext steht im Prompt

        local_val = run_local_validation(query=query, answer=answer, question_id=qid)

        rag_snippets = (
            build_rag_snippets_for_item(repo_root, cat, it)
            if cat in {"strahlenschutz", "pharmakologie", "rechtsmedizin"}
            else ""
        )

        qa_update: Dict[str, Any] = {
            "id": qid,
            "category": cat,
            "match_confidence": it.get("match_confidence"),
            "repair_status": it.get("repair_status"),
            "category_blob_preview": it.get("_validation_category_blob_preview"),
            "local_validation": {
                "available": local_val.get("available", False),
                "meta": (local_val.get("meta") or {}) if local_val.get("available") else {},
            },
            "rag_sources_used": [
                x.get("chunk_file")
                for x in (it.get("selected_chunks") or [])
                if isinstance(x, dict) and x.get("chunk_file")
            ],
        }

        # Default: nichts als verified markieren, solange MedGemma nicht wirklich lief
        qa_status = "unverified"
        validated_answer = None
        medgemma_payload = None

        # Template-Karten haben keinen belastbaren Fallkontext (Projektstandard: nicht halluzinieren).
        # Wir markieren sie deshalb direkt als needs_review (ohne MedGemma-Call).
        if (it.get("repair_status") or "").strip().lower() == "template":
            qa_status = "needs_review"
            qa_update["skipped_reason"] = "template_no_case_context"

        elif args.use_medgemma and medgemma_ready and medgemma_client is not None:
            system_prompt = build_system_prompt(cat)
            user_prompt = build_user_prompt(it, rag_snippets)
            try:
                medgemma_calls_attempted += 1
                # Budget gate (estimate)
                est_in = int((len(system_prompt) + len(user_prompt)) / 4)
                est_out = int(args.max_tokens)
                est_cost = (est_in / 1000) * COST_PER_1K_INPUT_USD + (est_out / 1000) * COST_PER_1K_OUTPUT_USD
                if spent_usd + est_cost > budget_usd:
                    qa_update["skipped_reason"] = "budget_exhausted_estimate"
                    qa_status = "unverified"
                    status_counts[qa_status] += 1
                    results.append(qa_update)
                    continue

                medgemma_payload = medgemma_client.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=int(args.max_tokens),
                )
                medgemma_calls_succeeded += 1

                # Update cost from real usage if available
                usage = medgemma_payload.get("usage", {}) or {}
                in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or est_in)
                out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or est_out)
                real_cost = (in_tok / 1000) * COST_PER_1K_INPUT_USD + (out_tok / 1000) * COST_PER_1K_OUTPUT_USD
                spent_usd += float(real_cost)

                parsed = parse_medgemma_output(medgemma_payload.get("text", ""))
                validated_answer = parsed.get("final_answer") or medgemma_payload.get("text", "")
                qa_status = parsed.get("qa_verdict") or "needs_review"

                # lokale Post-Checks auf der finalen Antwort
                post_val = run_local_validation(query=query, answer=validated_answer or "", question_id=f"{qid}_post")
                qa_update["post_validation"] = {
                    "available": post_val.get("available", False),
                    "meta": (post_val.get("meta") or {}) if post_val.get("available") else {},
                }

                # Wenn lokale Post-Validation hart rot flaggt → needs_review
                try:
                    is_valid = bool(((qa_update["post_validation"]["meta"] or {}).get("is_valid")))
                    conf = float(((qa_update["post_validation"]["meta"] or {}).get("confidence") or 0.0))
                    if (not is_valid) or conf < 0.65:
                        qa_status = "needs_review"
                except Exception:
                    qa_status = "needs_review"
            except Exception as e:
                # Wenn MedGemma gar nicht gelaufen ist, darf das NICHT als "needs_review" wirken,
                # sonst verlieren wir Kandidaten aus dem Pool. Daher: unverified + Fehlerlog.
                qa_status = "unverified"
                err = str(e)
                qa_update["medgemma_error"] = err
                qa_update["skipped_reason"] = "medgemma_call_failed"
                medgemma_errors[err.splitlines()[0][:120]] += 1

        # Write back (optional)
        if args.write_updated_batch:
            it["qa_status"] = qa_status
            it["qa_updated_at"] = datetime.now().isoformat(timespec="seconds")
            if validated_answer:
                it["validated_answer"] = validated_answer
            if medgemma_payload:
                it["medgemma_validation"] = {
                    "usage": medgemma_payload.get("usage", {}),
                    "qa_verdict": qa_status,
                    "response_preview": (medgemma_payload.get("text", "") or "")[:2000],
                }
            elif qa_update.get("medgemma_error"):
                it["medgemma_validation"] = {
                    "error": qa_update.get("medgemma_error"),
                }
            # Skipped reason sauber halten (alte Werte löschen, wenn diesmal nicht geskippt)
            if qa_update.get("skipped_reason"):
                it["qa_skipped_reason"] = qa_update.get("skipped_reason")
            else:
                if "qa_skipped_reason" in it:
                    del it["qa_skipped_reason"]

        status_counts[qa_status] += 1
        results.append(qa_update)

    # Report schreiben
    out_report.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []
    lines.append("# Validation Report (repaired cards)\n")
    lines.append(f"**Erstellt:** {now}\n")
    lines.append(f"**Input:** `{args.input}`\n")
    lines.append("**Filter:** `medgemma_relevant == true` AND `qa_status == unverified`\n")
    lines.append(f"**Gefunden:** {len(to_validate)} Kandidaten\n")
    if args.max_items and args.max_items > 0:
        lines.append(f"**Bearbeitet (max-items):** {len(enriched)}\n")
    else:
        lines.append(f"**Bearbeitet:** {len(enriched)}\n")

    lines.append("\n---\n")
    lines.append("## MedGemma/RAG Status\n")
    lines.append(f"- **use_medgemma:** {bool(args.use_medgemma)}\n")
    lines.append(f"- **medgemma_ready:** {bool(medgemma_ready)}\n")
    if medgemma_err:
        lines.append(f"- **medgemma_error:** `{medgemma_err}`\n")
    lines.append(f"- **medgemma_calls_attempted:** {medgemma_calls_attempted}\n")
    lines.append(f"- **medgemma_calls_succeeded:** {medgemma_calls_succeeded}\n")
    lines.append(f"- **budget_eur:** {args.budget_eur}\n")
    lines.append(f"- **spent_estimated_eur:** {round(spent_usd / EUR_USD_RATE, 4)}\n")
    if medgemma_errors:
        lines.append("\n### MedGemma Fehler (Top 5)\n")
        for msg, cnt in medgemma_errors.most_common(5):
            lines.append(f"- **{cnt}×** `{msg}`\n")

    lines.append("\n---\n")
    lines.append("## Verteilung nach Kategorie (Priorität)\n")
    for cat in ["strahlenschutz", "pharmakologie", "rechtsmedizin", "rest"]:
        lines.append(f"- **{cat}**: {cat_counts.get(cat, 0)}\n")

    lines.append("\n---\n")
    lines.append("## QA Status (nur bearbeitete Kandidaten)\n")
    for k in ["verified", "needs_review", "unverified"]:
        if k in status_counts:
            lines.append(f"- **{k}**: {status_counts[k]}\n")

    lines.append("\n---\n")
    lines.append("## Top 20 Prioritätsliste\n")
    lines.append("(Strahlenschutz → Pharmako → Rechtsmedizin → Rest nach niedriger match_confidence)\n\n")
    for it in enriched[:20]:
        qid = it.get("id") or f"repair_{it.get('original_index', 0):05d}"
        cat = it.get("_validation_category", "rest")
        mc = it.get("match_confidence")
        frage = (it.get("original_frage", "") or "").strip().replace("\n", " ")
        frage_short = (frage[:160] + "...") if len(frage) > 160 else frage
        dx = (it.get("extracted_context", {}) or {}).get("diagnose")
        lines.append(f"- **{qid}** | `{cat}` | match_confidence={mc} | dx={dx}\n")
        lines.append(f"  - Frage: {frage_short}\n")

    lines.append("\n---\n")
    lines.append("## Nächste Schritte / Run-Command\n")
    lines.append("Wenn MedGemma/Vertex konfiguriert ist, führe aus:\n\n")
    lines.append("```bash\n")
    lines.append("cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617\n")
    lines.append("python3 scripts/validate_repaired_cards.py --use-medgemma --write-updated-batch --budget-eur 5.0\n")
    lines.append("# Optional: nur fallbasierte Karten:\n")
    lines.append("#   --only-repaired\n")
    lines.append("# Optional: Template-Karten komplett überspringen:\n")
    lines.append("#   --skip-templates\n")
    lines.append("# Optional: falls gcloud nicht non-interaktiv refreshen kann:\n")
    lines.append("#   export GOOGLE_ACCESS_TOKEN='...'\n")
    lines.append("#   oder: --access-token '...'\n")
    lines.append("# Danach TSV neu erzeugen:\n")
    lines.append("python3 scripts/prepare_anki_repaired_import.py\n")
    lines.append("```\n")

    out_report.write_text("".join(lines), encoding="utf-8")

    # batch file schreiben (optional)
    if args.write_updated_batch:
        safe_backup_existing(in_path)
        write_jsonl(in_path, items)

    print(f"✅ Report erstellt: {out_report}")


if __name__ == "__main__":
    main()
