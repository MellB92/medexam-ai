#!/usr/bin/env python3
"""
Merge RemNote Exporte (.rem) inkrementell, ohne Raw-Dateien zu überschreiben.

Warum?
- RemNote `.rem` Exporte sind ZIP-Archive (u.a. `rem.json`, `cards.json`, `metadata.json`).
- Wir wollen neue + bestehende Exporte **zusammenführen**, ohne Duplikate zu erzeugen,
  und ohne alte Exporte zu überschreiben.

Merge-Regeln (konservativ, stabil):
- Default Primärschlüssel: `(knowledgebaseId, _id)` je Objekt.
  -> verhindert Kollisionen über verschiedene Knowledge Bases.
- Optional (empfohlen bei "gleiche Quelle, neuer Snapshot"):
  `--latest-per-root-title` wählt **pro Root-Titel** (z.B. "KP Münster 2020 -2025")
  nur den **neuesten** Export (nach `exportDate`). Damit entstehen **keine Duplikate**
  aus alten Snapshots, aber Raw-Dateien bleiben erhalten.
- Wenn derselbe Key mehrfach vorkommt: nimm den Eintrag mit der neueren `exportDate`.
- Raw-Exporte bleiben unverändert.

Outputs:
- `_OUTPUT/remnote_merge/rem_docs_merged.jsonl`  (ein JSON pro Rem-Doc)
- `_OUTPUT/remnote_merge/cards_merged.jsonl`     (ein JSON pro Card-Doc)
- `_OUTPUT/remnote_merge/exports_manifest.json`  (Metadaten + Hash je Export)
- `_OUTPUT/remnote_merge/remnote_merge_report.md`

Hinweis:
Diese Pipeline macht **keine** semantische Deduplizierung (Text-Gleichheit). Das ist optional,
aber ohne sauber decodierte RemNote-Textstruktur riskant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REM_FILES = ("rem.json", "cards.json", "metadata.json")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def parse_export_date(value: Any) -> str:
    # RemNote exportDate ist i.d.R. ISO string; wir lassen es als string.
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def export_date_is_newer(a: str, b: str) -> bool:
    """
    Vergleicht ISO Strings lexikografisch (funktioniert für RFC3339/ISO-8601 mit Z).
    Wenn unparsable: behandle als nicht neuer.
    """
    if not a or not b:
        return bool(a) and not bool(b)
    return a > b


@dataclass
class ExportMeta:
    file_path: str
    sha256: str
    exportDate: str
    exportVersion: Any
    knowledgebaseId: str
    userId: str
    name: str
    documentRemToExportId: str
    root_title: str
    rem_docs_count: int
    cards_docs_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "sha256": self.sha256,
            "exportDate": self.exportDate,
            "exportVersion": self.exportVersion,
            "knowledgebaseId": self.knowledgebaseId,
            "userId": self.userId,
            "name": self.name,
            "documentRemToExportId": self.documentRemToExportId,
            "root_title": self.root_title,
            "rem_docs_count": self.rem_docs_count,
            "cards_docs_count": self.cards_docs_count,
        }


def find_rem_exports(search_roots: list[Path]) -> list[Path]:
    exports: list[Path] = []
    seen: set[str] = set()
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("*.rem"):
            # Basic filter: only likely RemNote exports
            if p.name.lower().startswith("remnoteexport"):
                try:
                    key = str(p.resolve())
                except Exception:
                    key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                exports.append(p)
    # deterministic
    exports.sort(key=lambda x: (x.name, str(x)))
    return exports


def read_zip_json(z: zipfile.ZipFile, member: str) -> Dict[str, Any]:
    raw = z.read(member)
    return json.loads(raw)

def extract_root_title_from_rem_root(rem_root: Dict[str, Any]) -> str:
    """
    Root doc hat oft `k` wie "<prefix>.<Titel>" (z.B. "SEyzo... .KP Münster 2020 -2025").
    Wir verwenden den Teil nach dem letzten Punkt als Root-Titel.
    """
    try:
        root_id = rem_root.get("documentRemToExportId")
        docs = rem_root.get("docs") or []
        if isinstance(docs, list) and root_id:
            doc = next((d for d in docs if isinstance(d, dict) and d.get("_id") == root_id), None)
            k = doc.get("k") if isinstance(doc, dict) else None
            if isinstance(k, str) and k.strip():
                k = k.strip()
                if "." in k:
                    return k.split(".")[-1].strip()
                return k
    except Exception:
        pass
    return ""


def load_export(path: Path) -> Tuple[ExportMeta, list[dict], list[dict]]:
    sha = sha256_file(path)
    with zipfile.ZipFile(path, "r") as z:
        # rem.json
        rem_root = read_zip_json(z, "rem.json")
        rem_docs = rem_root.get("docs") or []
        if not isinstance(rem_docs, list):
            rem_docs = []

        # cards.json
        cards_root = read_zip_json(z, "cards.json")
        cards_docs = cards_root.get("docs") or []
        if not isinstance(cards_docs, list):
            cards_docs = []

    root_title = extract_root_title_from_rem_root(rem_root)
    meta = ExportMeta(
        file_path=str(path),
        sha256=sha,
        exportDate=parse_export_date(rem_root.get("exportDate")),
        exportVersion=rem_root.get("exportVersion"),
        knowledgebaseId=str(rem_root.get("knowledgebaseId") or ""),
        userId=str(rem_root.get("userId") or ""),
        name=str(rem_root.get("name") or ""),
        documentRemToExportId=str(rem_root.get("documentRemToExportId") or ""),
        root_title=str(root_title or ""),
        rem_docs_count=len(rem_docs),
        cards_docs_count=len(cards_docs),
    )
    return meta, rem_docs, cards_docs


def merge_by_kb_and_id(
    *,
    exports: list[ExportMeta],
    docs_by_export: dict[str, list[dict]],
    kind: str,
) -> Tuple[dict[Tuple[str, str], Dict[str, Any]], Dict[str, Any]]:
    """
    Returns:
      merged_map[(kb_id, obj_id)] = { ...record... }
      stats dict
    """
    merged: dict[Tuple[str, str], Dict[str, Any]] = {}
    collisions = 0
    replaced = 0
    missing_id = 0

    for meta in exports:
        kb = meta.knowledgebaseId or ""
        export_date = meta.exportDate or ""
        for obj in docs_by_export.get(meta.sha256, []):
            if not isinstance(obj, dict):
                continue
            obj_id = str(obj.get("_id") or "")
            if not obj_id:
                missing_id += 1
                continue
            key = (kb, obj_id)
            rec = {
                "kind": kind,
                "knowledgebaseId": kb,
                "exportDate": export_date,
                "export_sha256": meta.sha256,
                "export_file": meta.file_path,
                "object_id": obj_id,
                "object": obj,
            }
            if key not in merged:
                merged[key] = rec
            else:
                collisions += 1
                # choose newer exportDate
                if export_date_is_newer(export_date, str(merged[key].get("exportDate") or "")):
                    merged[key] = rec
                    replaced += 1

    stats = {
        "kind": kind,
        "unique_objects": len(merged),
        "collisions_same_key": collisions,
        "replaced_by_newer_export": replaced,
        "missing__id": missing_id,
    }
    return merged, stats


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search-root",
        action="append",
        default=[],
        help="Verzeichnis(e) zum Suchen nach RemNoteExport*.rem (mehrfach nutzbar).",
    )
    parser.add_argument(
        "--out-dir",
        default="_OUTPUT/remnote_merge",
        help="Output-Verzeichnis relativ zum Repo-Root.",
    )
    parser.add_argument(
        "--latest-per-root-title",
        action="store_true",
        help="Wählt pro Root-Titel (z.B. 'KP Münster 2020 -2025') nur den neuesten Export (nach exportDate).",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    out_dir = repo_root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Default search roots: repo_root + parent (damit Root-Workspace-Exports gefunden werden)
    roots = [Path(p) for p in (args.search_root or [])]
    if not roots:
        roots = [repo_root, repo_root.parent]

    exports_paths = find_rem_exports(roots)
    if not exports_paths:
        raise SystemExit(f"❌ Keine RemNoteExport*.rem gefunden unter: {', '.join(str(r) for r in roots)}")

    export_metas_all: list[ExportMeta] = []
    rem_docs_by_sha: dict[str, list[dict]] = {}
    cards_docs_by_sha: dict[str, list[dict]] = {}

    for p in exports_paths:
        meta, rem_docs, cards_docs = load_export(p)
        export_metas_all.append(meta)
        rem_docs_by_sha[meta.sha256] = rem_docs
        cards_docs_by_sha[meta.sha256] = cards_docs

    # Auswahl: latest per root-title (empfohlen für "gleiche Quelle" Snapshots)
    selected: list[ExportMeta] = list(export_metas_all)
    if args.latest_per_root_title:
        by_title: dict[str, ExportMeta] = {}
        for m in export_metas_all:
            title = m.root_title or ""
            if not title:
                # ohne Titel: nicht dedupen, separat behalten
                title = f"__no_title__::{m.sha256}"
            if title not in by_title:
                by_title[title] = m
            else:
                if export_date_is_newer(m.exportDate, by_title[title].exportDate):
                    by_title[title] = m
        selected = list(by_title.values())
        selected.sort(key=lambda x: (x.root_title, x.exportDate, x.file_path))

    # Manifest
    manifest_path = out_dir / "exports_manifest.json"
    safe_backup_existing(manifest_path)
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "export_files_found": [str(p) for p in exports_paths],
        "exports_all": [m.to_dict() for m in export_metas_all],
        "selected_mode": "latest_per_root_title" if args.latest_per_root_title else "all_exports",
        "selected_exports_sha256": [m.sha256 for m in selected],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Merge
    merged_rem, rem_stats = merge_by_kb_and_id(exports=selected, docs_by_export=rem_docs_by_sha, kind="rem")
    merged_cards, cards_stats = merge_by_kb_and_id(exports=selected, docs_by_export=cards_docs_by_sha, kind="card")

    # Write JSONL (stable order)
    rem_out = out_dir / "rem_docs_merged.jsonl"
    cards_out = out_dir / "cards_merged.jsonl"
    safe_backup_existing(rem_out)
    safe_backup_existing(cards_out)

    rem_records = [merged_rem[k] for k in sorted(merged_rem.keys(), key=lambda t: (t[0], t[1]))]
    card_records = [merged_cards[k] for k in sorted(merged_cards.keys(), key=lambda t: (t[0], t[1]))]

    if not args.dry_run:
        write_jsonl(rem_out, rem_records)
        write_jsonl(cards_out, card_records)

    # Report
    report_path = out_dir / "remnote_merge_report.md"
    safe_backup_existing(report_path)

    # Per knowledgebase counts
    kb_counts = {}
    for m in export_metas_all:
        kb_counts.setdefault(m.knowledgebaseId, {"exports": 0, "rem_docs": 0, "cards_docs": 0, "names": set()})
        kb_counts[m.knowledgebaseId]["exports"] += 1
        kb_counts[m.knowledgebaseId]["rem_docs"] += m.rem_docs_count
        kb_counts[m.knowledgebaseId]["cards_docs"] += m.cards_docs_count
        if m.name:
            kb_counts[m.knowledgebaseId]["names"].add(m.name)

    lines: list[str] = []
    lines.append("# RemNote Merge Report\n\n")
    lines.append(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append("## Gefundene Exporte\n\n")
    selected_set = {m.sha256 for m in selected}
    for m in export_metas_all:
        sel = " ✅ SELECTED" if m.sha256 in selected_set else ""
        lines.append(
            f"- `{Path(m.file_path).name}` | root=`{m.root_title}` | kb=`{m.knowledgebaseId}` | exportDate=`{m.exportDate}` | "
            f"rem_docs={m.rem_docs_count} | cards={m.cards_docs_count}{sel}\n"
        )

    lines.append("\n## Knowledgebase-Übersicht\n\n")
    for kb, d in kb_counts.items():
        names = ", ".join(sorted(d["names"])) if d["names"] else "-"
        lines.append(
            f"- kb=`{kb}` | exports={d['exports']} | rem_docs(sum)={d['rem_docs']} | cards(sum)={d['cards_docs']} | names={names}\n"
        )

    lines.append("\n## Merge-Statistik\n\n")
    lines.append(f"- **rem**: unique={rem_stats['unique_objects']} | collisions={rem_stats['collisions_same_key']} | replaced={rem_stats['replaced_by_newer_export']} | missing__id={rem_stats['missing__id']}\n")
    lines.append(f"- **cards**: unique={cards_stats['unique_objects']} | collisions={cards_stats['collisions_same_key']} | replaced={cards_stats['replaced_by_newer_export']} | missing__id={cards_stats['missing__id']}\n")

    lines.append("\n## Outputs\n\n")
    lines.append(f"- `{manifest_path}`\n")
    lines.append(f"- `{report_path}`\n")
    if args.dry_run:
        lines.append("- (dry-run) JSONL wurde nicht geschrieben\n")
    else:
        lines.append(f"- `{rem_out}`\n")
        lines.append(f"- `{cards_out}`\n")

    lines.append("\n## Empfehlung (Best Practice)\n\n")
    lines.append("- **Raw-Exporte nie überschreiben** (append-only). Neue Exporte einfach hinzufügen.\n")
    lines.append("- Dedupe/Upsert nur in **kanonischen Outputs** (JSONL/DB), nicht in den Raw-Dateien.\n")
    lines.append("- Wenn du *semantisch* Deduplizieren willst (zwischen KBs): erst Text sauber aus Rem-Struktur extrahieren, dann Fingerprint.\n")

    report_path.write_text("".join(lines), encoding="utf-8")

    print(f"✅ Manifest: {manifest_path}")
    print(f"✅ Report:   {report_path}")
    if not args.dry_run:
        print(f"✅ rem.json merged (jsonl):   {rem_out}")
        print(f"✅ cards.json merged (jsonl): {cards_out}")


if __name__ == "__main__":
    main()


