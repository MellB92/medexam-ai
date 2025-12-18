#!/usr/bin/env python3
"""Exportiert sofort nutzbare Lern-Exports aus `evidenz_antworten_enriched_for_srs*.json`.

Ziele (Outputs immer mit Timestamp, nichts wird überschrieben):
- Anki-TSV (Front/Back/Tags) für "ready" Karten
- Anki-TSV Review-Queue (nur needs_review + needs_context), Back = bestehende Antwort + Review-Hinweise
- Study-Dashboard (Markdown) mit Counts pro Fachgebiet × Status
- Optional: Daily-Plan (JSON) mit stratifizierter Auswahl aus ready-Karten

Harte Constraints
- `_OUTPUT/evidenz_antworten.json` wird NICHT geschrieben/überschrieben.
- Keine Rewrites/Neugenerierung von Antworten (nur TSV-sichere Formatierung: Tabs/Newlines).
- Keine Secrets in Logs.

Hinweis
- Die Input-JSON kann entweder eine Liste von Items sein (neueres Format)
  oder ein Objekt mit `items: [...]` (älteres Format). Beides wird unterstützt.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


@dataclass(frozen=True)
class ExportPaths:
    anki_ready: Path
    anki_review_queue: Path
    dashboard: Path
    daily_plan: Optional[Path]


_TAG_CLEAN_RE = re.compile(r"[^\w:.-]+", flags=re.UNICODE)


def _now_ts() -> str:
    # Sekunden-Granularität, damit wiederholte Runs nicht kollidieren.
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _unique_path(path: Path) -> Path:
    """Verhindert Überschreiben: hängt _1, _2, ... an, falls Datei existiert."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for i in range(1, 10_000):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Konnte keinen freien Dateinamen finden für: {path}")


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _tsv_safe_field(text: str) -> str:
    """Macht Text TSV-sicher (keine Tabs/Zeilenumbrüche), ohne inhaltliche Neuschreibung."""
    t = _coerce_str(text)

    # Problematische Separatoren/CR entfernen
    t = t.replace("\u2028", " ").replace("\u2029", " ")
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    # Tabs dürfen nicht in TSV-Feldern vorkommen.
    t = t.replace("\t", " ")

    # Zeilenumbrüche in Anki als HTML-Linebreak darstellen.
    t = t.replace("\n", "<br>")

    # Anki importiert führende/trailing Spaces oft ok; wir trimmen minimal.
    return t.strip()


def _normalize_tag(tag: str) -> str:
    """Normalisiert Tags für Anki: keine Spaces, keine Kommas, robuste Zeichenmenge."""
    t = _coerce_str(tag).strip()
    if not t:
        return ""

    # Kommas sind häufig Quelle für "Komma-Chaos".
    t = t.replace(",", " ")

    # Whitespace zu _
    t = " ".join(t.split())
    t = t.replace(" ", "_")

    # Übrige Sonderzeichen in _
    t = _TAG_CLEAN_RE.sub("_", t)

    # Mehrfach-Underscores reduzieren
    t = re.sub(r"_+", "_", t)
    t = t.strip("_")
    return t


def _map_status(study_status: str) -> str:
    s = _coerce_str(study_status).strip().lower()
    if s == "ready":
        return "ready"
    if s == "needs_review":
        return "review"
    if s == "needs_context":
        return "context"
    if s == "unknown":
        return "unknown"
    if s == "skip_fragment":
        return "skip_fragment"
    # Fallback
    return "unknown"


def _extract_factcheck(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    validation = entry.get("validation")
    if not isinstance(validation, dict):
        return None
    fc = validation.get("perplexity_factcheck")
    return fc if isinstance(fc, dict) else None


def _format_review_hints(entry: Dict[str, Any]) -> str:
    """Erzeugt Review-Hinweise (deutsch) aus Factcheck-Issues/Sources etc."""
    lines: List[str] = []

    study_status = _coerce_str(entry.get("study_status")).strip()
    exclude_reason = _coerce_str(entry.get("study_exclude_reason")).strip()

    lines.append("Review-Hinweise")
    if study_status:
        lines.append(f"Status: {study_status}")
    if exclude_reason:
        lines.append(f"Ausschlussgrund: {exclude_reason}")

    source_file = _coerce_str(entry.get("source_file")).strip()
    if source_file:
        lines.append(f"Quelle (Datei): {source_file}")

    leitlinie = _coerce_str(entry.get("leitlinie")).strip()
    if leitlinie:
        lines.append(f"Leitlinie/Referenz: {leitlinie}")

    fc = _extract_factcheck(entry)
    if fc:
        verdict = _coerce_str(fc.get("verdict")).strip()
        if verdict:
            lines.append(f"Factcheck-Verdikt: {verdict}")

        issues = fc.get("issues")
        if isinstance(issues, list):
            issues_clean = [str(x).strip() for x in issues if str(x).strip()]
        else:
            issues_clean = []

        if issues_clean:
            lines.append("Probleme (Issues):")
            for it in issues_clean:
                lines.append(f"- {it}")

        sources = fc.get("suggested_sources")
        sources_clean: List[str] = []
        if isinstance(sources, list):
            for s in sources:
                if not isinstance(s, dict):
                    continue
                title = _coerce_str(s.get("title")).strip()
                url = _coerce_str(s.get("url")).strip()
                why = _coerce_str(s.get("why")).strip()
                if title and url:
                    line = f"- {title}: {url}"
                elif url:
                    line = f"- {url}"
                elif title:
                    line = f"- {title}"
                else:
                    continue
                if why:
                    line = f"{line} (Warum: {why})"
                sources_clean.append(line)

        if sources_clean:
            lines.append("Empfohlene Quellen:")
            lines.extend(sources_clean)

        report_file = _coerce_str(fc.get("report_file")).strip()
        if report_file:
            lines.append(f"Factcheck-Bericht: {report_file}")

        patched_at = _coerce_str(fc.get("patched_at")).strip()
        if patched_at:
            lines.append(f"Gepatcht am: {patched_at}")

        patched_from = _coerce_str(fc.get("patched_from")).strip()
        if patched_from:
            lines.append(f"Gepatcht aus: {patched_from}")

        meta = fc.get("meta")
        if isinstance(meta, dict) and meta:
            # bewusst kompakt halten
            meta_parts = []
            for k in ("perplexity_model", "timestamp", "sample_pos", "retry_from"):
                v = meta.get(k)
                if v is None:
                    continue
                vs = _coerce_str(v).strip()
                if vs:
                    meta_parts.append(f"{k}={vs}")
            if meta_parts:
                lines.append("Meta: " + ", ".join(meta_parts))

    # Wenn außer Überschrift gar nichts da ist, leer zurückgeben.
    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def _build_tags(
    entry: Dict[str, Any],
    *,
    status_mapped: str,
    fachgebiet_fallback: str,
) -> List[str]:
    tags: List[str] = []

    fach = _coerce_str(entry.get("fachgebiet")).strip() or fachgebiet_fallback
    fach_tag = _normalize_tag(f"fachgebiet:{fach}")
    if fach_tag:
        tags.append(fach_tag)

    tags.append(_normalize_tag("source:medexamenai"))

    if status_mapped:
        tags.append(_normalize_tag(f"status:{status_mapped}"))

    if bool(entry.get("is_meaningful")):
        tags.append(_normalize_tag("meaningful"))

    exclude_reason = _coerce_str(entry.get("study_exclude_reason")).strip()
    if exclude_reason and status_mapped in {"review", "context", "unknown"}:
        tags.append(_normalize_tag(f"exclude:{exclude_reason}"))

    # Dedup + Filter
    out = []
    seen = set()
    for t in tags:
        tt = _normalize_tag(t)
        if not tt:
            continue
        if "," in tt:
            # sollte durch Normalisierung nicht passieren
            tt = tt.replace(",", "_")
        if tt not in seen:
            seen.add(tt)
            out.append(tt)

    # deterministisch
    out.sort()
    return out


def _parse_input_payload(payload: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Unterstützt zwei Input-Formate: list[dict] oder {items: list[dict], ...meta}."""
    if isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
        return items, {}

    if isinstance(payload, dict):
        maybe_items = payload.get("items")
        if isinstance(maybe_items, list):
            items = [x for x in maybe_items if isinstance(x, dict)]
            meta = {k: v for k, v in payload.items() if k != "items"}
            return items, meta

    raise ValueError("Input JSON muss Liste oder Objekt mit `items` sein")


def _pick_default_input(output_dir: Path) -> Path:
    """Wählt Default-Input: fixed_* (neueste) > gewünschter Standard > neuestes enriched_for_srs_*"""
    # 1) fixed Variante (neueste mtime)
    fixed = sorted(
        output_dir.glob("evidenz_antworten_enriched_for_srs_fixed_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if fixed:
        return fixed[0]

    # 2) expliziter Standard aus Task
    preferred = output_dir / "evidenz_antworten_enriched_for_srs_20251215_1529.json"
    if preferred.exists():
        return preferred

    # 3) fallback: neuestes enriched_for_srs_*.json
    candidates = sorted(
        output_dir.glob("evidenz_antworten_enriched_for_srs_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        "Kein Input gefunden. Erwartet z.B. _OUTPUT/evidenz_antworten_enriched_for_srs_*.json"
    )


def _write_tsv(path: Path, rows: Iterable[Tuple[str, str, str]]) -> int:
    """Schreibt TSV ohne Header. Gibt Anzahl Zeilen zurück."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for front, back, tags in rows:
            f.write(front)
            f.write("\t")
            f.write(back)
            f.write("\t")
            f.write(tags)
            f.write("\n")
            n += 1
    return n


def _dashboard_markdown(
    *,
    source_file: str,
    ts: str,
    totals: Dict[str, int],
    per_fach: Dict[str, Counter[str]],
    top_review: List[Tuple[str, int]],
    ready_cards_total: int,
    expected_ready_cards_total: Optional[int],
    skipped_fragments_total: int,
    missing_fachgebiet_meaningful: int,
    empty_q_or_a_skipped: int,
) -> str:
    lines: List[str] = []
    lines.append(f"# Lern-Dashboard ({ts})")
    lines.append("")
    lines.append(f"Quelle: `{source_file}`")
    lines.append("")

    lines.append("## Zusammenfassung")
    lines.append("")
    lines.append(f"- Gesamt (alle Items): **{totals.get('all_items', 0)}**")
    lines.append(f"- Meaningful (markiert): **{totals.get('meaningful', 0)}**")
    lines.append(f"- ready_cards_total (ready & meaningful): **{ready_cards_total}**")
    if expected_ready_cards_total is not None:
        if ready_cards_total == expected_ready_cards_total:
            lines.append(
                f"- Plausibilitätsprüfung: ready_cards_total entspricht Erwartung (**{expected_ready_cards_total}**)"
            )
        else:
            lines.append(
                f"- Plausibilitätsprüfung: ready_cards_total erwartet **{expected_ready_cards_total}**, ist aber **{ready_cards_total}**"
            )
    lines.append(
        f"- skip_fragment (aus Dashboard/Exports ausgeschlossen): **{skipped_fragments_total}**"
    )
    if missing_fachgebiet_meaningful:
        lines.append(
            f"- Achtung: Meaningful ohne Fachgebiet (Fallback 'unbekannt'): **{missing_fachgebiet_meaningful}**"
        )
    if empty_q_or_a_skipped:
        lines.append(
            f"- Übersprungen wegen leerer Frage/Antwort (Export-Validierung): **{empty_q_or_a_skipped}**"
        )
    lines.append("")

    lines.append("## Counts pro Fachgebiet × Status")
    lines.append("")
    lines.append("Status-Spalten: ready / review / context / unknown")
    lines.append("")

    header = "| Fachgebiet | ready | review | context | unknown | total |"
    sep = "|---|---:|---:|---:|---:|---:|"
    lines.append(header)
    lines.append(sep)

    # sort: zuerst nach review, dann total
    def sort_key(item: Tuple[str, Counter[str]]) -> Tuple[int, int, str]:
        fach, c = item
        return (
            -int(c.get("review", 0)),
            -int(
                c.get("ready", 0)
                + c.get("review", 0)
                + c.get("context", 0)
                + c.get("unknown", 0)
            ),
            fach,
        )

    for fach, c in sorted(per_fach.items(), key=sort_key):
        r = int(c.get("ready", 0))
        rv = int(c.get("review", 0))
        cx = int(c.get("context", 0))
        uk = int(c.get("unknown", 0))
        total = r + rv + cx + uk
        lines.append(f"| {fach} | {r} | {rv} | {cx} | {uk} | {total} |")

    lines.append("")
    lines.append("## Top 20 Fachgebiete nach needs_review")
    lines.append("")
    lines.append("| Rang | Fachgebiet | needs_review |")
    lines.append("|---:|---|---:|")
    for i, (fach, n) in enumerate(top_review[:20], start=1):
        lines.append(f"| {i} | {fach} | {n} |")

    lines.append("")
    return "\n".join(lines)


def _stratified_sample(
    groups: Dict[str, List[int]],
    *,
    total_n: int,
    rng: random.Random,
) -> Dict[str, List[int]]:
    """Stratifizierte Stichprobe: möglichst balanciert nach Fachgebiet."""
    if total_n <= 0:
        return {}

    non_empty = {k: v for k, v in groups.items() if v}
    if not non_empty:
        return {}

    keys = sorted(non_empty.keys())

    # Fall: mehr Fachgebiete als Karten -> 1 pro Fachgebiet für die größten Gruppen
    if len(keys) >= total_n:
        # sort nach Gruppengröße (desc), tie-break alphabetisch
        keys_by_size = sorted(keys, key=lambda k: (-len(non_empty[k]), k))
        chosen_keys = keys_by_size[:total_n]
        out: Dict[str, List[int]] = {}
        for k in chosen_keys:
            out[k] = [rng.choice(non_empty[k])]
        return out

    # Basisallokation
    base = total_n // len(keys)
    remainder = total_n % len(keys)

    out = {k: [] for k in keys}

    # erst base ziehen
    remaining_pool = {k: list(v) for k, v in non_empty.items()}
    for k in keys:
        want = min(base, len(remaining_pool[k]))
        if want <= 0:
            continue
        picks = rng.sample(remaining_pool[k], k=want)
        out[k].extend(picks)
        picked_set = set(picks)
        remaining_pool[k] = [x for x in remaining_pool[k] if x not in picked_set]

    # remainder verteilen: bevorzugt auf Gruppen mit noch Rest
    # iterativ, damit leere Gruppen übersprungen werden
    while remainder > 0:
        progress = False
        keys_by_rest = sorted(keys, key=lambda k: (-len(remaining_pool[k]), k))
        for k in keys_by_rest:
            if remainder <= 0:
                break
            if not remaining_pool[k]:
                continue
            out[k].append(rng.choice(remaining_pool[k]))
            last = out[k][-1]
            remaining_pool[k].remove(last)
            remainder -= 1
            progress = True
        if not progress:
            break

    # Falls wir wegen zu kleiner Gruppen nicht auf total_n kommen, auffüllen aus allen Resten
    selected = sum(len(v) for v in out.values())
    if selected < total_n:
        rest_flat: List[Tuple[str, int]] = []
        for k in keys:
            rest_flat.extend((k, idx) for idx in remaining_pool[k])
        rng.shuffle(rest_flat)
        for k, idx in rest_flat:
            if selected >= total_n:
                break
            out[k].append(idx)
            selected += 1

    # leere entfernen
    out = {k: v for k, v in out.items() if v}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Exportiert Anki-TSVs + Dashboard aus evidenz_antworten_enriched_for_srs*.json (ohne Rewrites)"
        )
    )
    parser.add_argument(
        "--input",
        default="",
        help=(
            "Pfad zur enriched JSON. Default: neueste fixed_* falls vorhanden, sonst Standard/neueste enriched_for_srs_*"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output-Verzeichnis (default: _OUTPUT)",
    )
    parser.add_argument(
        "--include-non-meaningful",
        action="store_true",
        help="Wenn gesetzt, werden auch nicht-meaningful Items exportiert.",
    )
    parser.add_argument(
        "--daily-plan",
        action="store_true",
        help="Optional: Erzeugt zusätzlich daily_plan_<TS>.json",
    )
    parser.add_argument(
        "--daily-n",
        type=int,
        default=30,
        help="Anzahl Karten im Daily-Plan (default: 30)",
    )
    parser.add_argument(
        "--seed",
        default="",
        help="Seed für Daily-Plan (default: YYYYMMDD)",
    )

    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    in_path = Path(args.input) if args.input else _pick_default_input(out_dir)
    if not in_path.exists():
        raise SystemExit(f"Input nicht gefunden: {in_path}")

    ts = _now_ts()

    paths = ExportPaths(
        anki_ready=_unique_path(out_dir / f"anki_ready_{ts}.tsv"),
        anki_review_queue=_unique_path(out_dir / f"anki_review_queue_{ts}.tsv"),
        dashboard=_unique_path(out_dir / f"study_dashboard_{ts}.md"),
        daily_plan=(
            _unique_path(out_dir / f"daily_plan_{ts}.json") if args.daily_plan else None
        ),
    )

    payload = _read_json(in_path)
    items, _meta = _parse_input_payload(payload)

    # Zählwerke
    totals: Dict[str, int] = {
        "all_items": len(items),
        "meaningful": 0,
    }

    per_fach: Dict[str, Counter[str]] = defaultdict(Counter)
    needs_review_by_fach: Counter[str] = Counter()

    missing_fachgebiet_meaningful = 0
    empty_q_or_a_skipped = 0
    skipped_fragments_total = 0

    # Export-Row Sammler
    ready_rows: List[Tuple[str, str, str]] = []
    review_rows: List[Tuple[str, str, str]] = []

    for idx, entry in enumerate(items):
        if not isinstance(entry, dict):
            continue

        is_meaningful = bool(entry.get("is_meaningful"))
        if is_meaningful:
            totals["meaningful"] += 1

        fach_raw = _coerce_str(entry.get("fachgebiet")).strip()
        fach = fach_raw if fach_raw else "unbekannt"

        if is_meaningful and not fach_raw:
            missing_fachgebiet_meaningful += 1

        mapped = _map_status(entry.get("study_status"))
        if mapped == "skip_fragment":
            skipped_fragments_total += 1
            continue

        # Dashboard zählt per Fachgebiet (optional meaningful-only)
        if args.include_non_meaningful or is_meaningful:
            per_fach[fach][mapped] += 1
            if mapped == "review":
                needs_review_by_fach[fach] += 1

        # Exporte: nur meaningful, wenn nicht explizit anders
        if not (args.include_non_meaningful or is_meaningful):
            continue

        q_raw = _coerce_str(entry.get("frage")).strip()
        a_raw = _coerce_str(entry.get("antwort")).strip()
        if not q_raw or not a_raw:
            empty_q_or_a_skipped += 1
            continue

        front = _tsv_safe_field(q_raw)
        if mapped == "ready":
            back = _tsv_safe_field(a_raw)
        else:
            back = _tsv_safe_field(a_raw)  # default

        if not front or not back:
            empty_q_or_a_skipped += 1
            continue

        tags_list = _build_tags(
            entry, status_mapped=mapped, fachgebiet_fallback="unbekannt"
        )
        tags = " ".join(tags_list)

        # Validierung: keine leeren Tags bei meaningful (mind. fachgebiet + source)
        if is_meaningful and ("fachgebiet:" not in tags):
            raise SystemExit(
                f"Validierungsfehler: fachgebiet-Tag fehlt trotz meaningful (index={idx})"
            )
        if "," in tags:
            raise SystemExit(f"Validierungsfehler: Komma im Tag-String (index={idx})")

        # ready export
        if mapped == "ready":
            ready_rows.append((front, back, tags))

        # review queue export
        if mapped in {"review", "context"}:
            hints = _format_review_hints(entry)
            if hints:
                back_review = _tsv_safe_field(a_raw + "\n\n---\n" + hints)
            else:
                back_review = _tsv_safe_field(a_raw)
            review_rows.append((front, back_review, tags))

    # ready_cards_total meaningful-only ready (ohne leere Q/A)
    ready_cards_total = len(ready_rows)

    # Outputs schreiben
    n_ready = _write_tsv(paths.anki_ready, ready_rows)
    n_review = _write_tsv(paths.anki_review_queue, review_rows)

    top_review = needs_review_by_fach.most_common(20)

    dashboard = _dashboard_markdown(
        source_file=in_path.name,
        ts=ts,
        totals=totals,
        per_fach=per_fach,
        top_review=top_review,
        ready_cards_total=ready_cards_total,
        expected_ready_cards_total=2090,
        skipped_fragments_total=skipped_fragments_total,
        missing_fachgebiet_meaningful=missing_fachgebiet_meaningful,
        empty_q_or_a_skipped=empty_q_or_a_skipped,
    )
    _write_text(paths.dashboard, dashboard)

    # Optional daily plan
    if paths.daily_plan is not None:
        # Gruppen (nur ready_rows) nach Fachgebiet aus dem Tag fachgebiet:* ableiten
        groups: Dict[str, List[int]] = defaultdict(list)
        idx_to_card: Dict[int, Dict[str, Any]] = {}

        # wir verwenden die selben Filter wie ready_rows (meaningful-only default)
        # Dazu brauchen wir nochmals die Indizes der ready Items: wir rekonstruieren über items
        for i, entry in enumerate(items):
            if not isinstance(entry, dict):
                continue
            if not (args.include_non_meaningful or bool(entry.get("is_meaningful"))):
                continue
            if _map_status(entry.get("study_status")) != "ready":
                continue
            q_raw = _coerce_str(entry.get("frage")).strip()
            a_raw = _coerce_str(entry.get("antwort")).strip()
            if not q_raw or not a_raw:
                continue
            fach_raw = _coerce_str(entry.get("fachgebiet")).strip() or "unbekannt"
            groups[fach_raw].append(i)
            idx_to_card[i] = {
                "id": f"evidenz_{i}",
                "fachgebiet": fach_raw,
                "frage": q_raw,
                "status": _coerce_str(entry.get("study_status")).strip(),
            }

        seed = args.seed.strip() or datetime.now().strftime("%Y%m%d")
        rng = random.Random(seed)

        sampled = _stratified_sample(groups, total_n=int(args.daily_n), rng=rng)
        chosen: List[Dict[str, Any]] = []
        per_fach_counts: Dict[str, int] = {}
        for fach, idxs in sampled.items():
            per_fach_counts[fach] = len(idxs)
            for i in idxs:
                chosen.append(idx_to_card[i])

        chosen.sort(key=lambda d: (d.get("fachgebiet", ""), d.get("id", "")))

        daily_payload = {
            "zeitstempel": datetime.now().isoformat(),
            "quelle": in_path.name,
            "seed": seed,
            "strategie": "stratifiziert_nach_fachgebiet",
            "angefordert_n": int(args.daily_n),
            "gesamt": len(chosen),
            "pro_fachgebiet": dict(
                sorted(per_fach_counts.items(), key=lambda x: (-x[1], x[0]))
            ),
            "karten": chosen,
        }
        _write_json(paths.daily_plan, daily_payload)

    # Logs (Deutsch, keine Secrets)
    print("Export abgeschlossen.")
    print(f"Input: {in_path}")
    print(f"Anki ready TSV: {paths.anki_ready} ({n_ready} Zeilen)")
    print(f"Anki review TSV: {paths.anki_review_queue} ({n_review} Zeilen)")
    print(f"Dashboard: {paths.dashboard}")
    if paths.daily_plan is not None:
        print(f"Daily-Plan: {paths.daily_plan}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())




