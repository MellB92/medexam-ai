#!/usr/bin/env python3
"""
Extrahiert RemNote `.rem` (ZIP) Exporte in eine kanonische, textbasierte Wissensbasis.

Motivation:
- `.rem` ist RemNote-intern (IDs können sich zwischen Snapshots ändern).
- Für RAG/Validierung brauchen wir **Text** + stabile Metadaten.

Input:
- `_OUTPUT/remnote_merge/exports_manifest.json` (von `scripts/merge_remnote_exports.py`)
  oder direkt `--export-file` (Pfad zur .rem Datei)

Output:
- `_OUTPUT/remnote_merge/remnote_extracted_nodes.jsonl`
- `_OUTPUT/remnote_merge/remnote_extracted_outline.md`
- `_OUTPUT/remnote_merge/remnote_extraction_report.md`

Duplikatfreiheit:
- Verwende vorher `scripts/merge_remnote_exports.py --latest-per-root-title`
  (selektiert pro Root-Titel nur den neuesten Snapshot).
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "remnote"


def load_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_export_from_manifest(manifest: Dict[str, Any], root_title: Optional[str] = None) -> Dict[str, Any]:
    exports = manifest.get("exports_all") or []
    if not isinstance(exports, list) or not exports:
        raise ValueError("exports_manifest.json hat kein gültiges exports_all[]")

    selected_shas = manifest.get("selected_exports_sha256") or []
    if isinstance(selected_shas, list) and selected_shas:
        sha = selected_shas[0]
        ex = next((e for e in exports if e.get("sha256") == sha), None)
        if ex:
            return ex

    # Fallback: newest by exportDate (lexicographic works for ISO strings)
    candidates = exports
    if root_title:
        candidates = [e for e in exports if str(e.get("root_title") or "").strip() == root_title]
        if not candidates:
            raise ValueError(f"Kein Export mit root_title={root_title!r} gefunden.")

    candidates.sort(key=lambda e: str(e.get("exportDate") or ""))
    return candidates[-1]


def read_rem_json(export_file: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(export_file, "r") as z:
        raw = z.read("rem.json")
    return json.loads(raw)


def extract_text_from_key_field(key_field: Any) -> str:
    """
    RemNote speichert sichtbaren Text häufig in `key: [...]`.
    In vielen Fällen ist das eine Liste von Strings.
    """
    if isinstance(key_field, str):
        return key_field.strip()

    if isinstance(key_field, list):
        parts: list[str] = []
        for it in key_field:
            if isinstance(it, str):
                s = it.strip()
                if s:
                    parts.append(s)
            elif isinstance(it, dict):
                # best-effort: häufige string keys
                for k in ("s", "text", "t", "value"):
                    v = it.get(k)
                    if isinstance(v, str) and v.strip():
                        parts.append(v.strip())
        return " ".join(parts).strip()

    return ""


def build_tree(docs: List[Dict[str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    id_map: Dict[str, Dict[str, Any]] = {}
    children_by_parent: Dict[str, List[str]] = {}

    for d in docs:
        if not isinstance(d, dict):
            continue
        _id = d.get("_id")
        if not isinstance(_id, str) or not _id:
            continue
        id_map[_id] = d

    for _id, d in id_map.items():
        parent = d.get("parent")
        if isinstance(parent, str) and parent:
            children_by_parent.setdefault(parent, []).append(_id)

    # stabilize fallback ordering by `x` then createdAt
    def sort_children(parent_id: str) -> List[str]:
        arr = children_by_parent.get(parent_id, [])
        return sorted(
            arr,
            key=lambda cid: (
                int(id_map.get(cid, {}).get("x") or 0),
                int(id_map.get(cid, {}).get("createdAt") or 0),
                cid,
            ),
        )

    for pid in list(children_by_parent.keys()):
        children_by_parent[pid] = sort_children(pid)

    return id_map, children_by_parent


def iter_subtree(
    *,
    root_id: str,
    id_map: Dict[str, Dict[str, Any]],
    children_by_parent: Dict[str, List[str]],
) -> Iterable[Tuple[Dict[str, Any], int, List[str]]]:
    """
    Yields: (node_dict, depth, path_titles)
    """
    visited: set[str] = set()

    def children_of(node_id: str) -> List[str]:
        node = id_map.get(node_id) or {}
        ch = node.get("ch")
        if isinstance(ch, list) and ch and all(isinstance(x, str) for x in ch):
            # preserve RemNote order, but filter to known ids
            return [x for x in ch if x in id_map]
        return children_by_parent.get(node_id, [])

    def dfs(node_id: str, depth: int, path: List[str]) -> None:
        if node_id in visited:
            return
        visited.add(node_id)

        node = id_map.get(node_id)
        if not node:
            return

        title = extract_text_from_key_field(node.get("key"))
        # Path always includes something stable (fallback to id)
        path2 = path + ([title] if title else [node_id])
        yield_items.append((node, depth, path2))

        for cid in children_of(node_id):
            dfs(cid, depth + 1, path2)

    # Workaround for Python nested generator with side effects
    yield_items: List[Tuple[Dict[str, Any], int, List[str]]] = []
    dfs(root_id, 0, [])
    return yield_items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="_OUTPUT/remnote_merge/exports_manifest.json")
    parser.add_argument("--export-file", default="", help="Direkter Pfad zur .rem Datei (überschreibt manifest).")
    parser.add_argument("--root-title", default="", help="Optional: Root-Titel (wenn manifest nicht selektiert ist).")
    parser.add_argument("--out-dir", default="_OUTPUT/remnote_merge")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    out_dir = repo_root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    export_meta: Dict[str, Any]
    export_file: Path

    if args.export_file:
        export_file = Path(args.export_file).expanduser()
        export_meta = {"file_path": str(export_file), "exportDate": "", "sha256": "", "knowledgebaseId": "", "root_title": args.root_title}
    else:
        manifest = load_manifest(repo_root / args.manifest)
        export_meta = select_export_from_manifest(manifest, root_title=(args.root_title or None))
        export_file = Path(export_meta["file_path"])

    if not export_file.exists():
        raise SystemExit(f"❌ Export-Datei nicht gefunden: {export_file}")

    rem_root = read_rem_json(export_file)
    docs = rem_root.get("docs") or []
    if not isinstance(docs, list):
        raise SystemExit("❌ rem.json: docs ist nicht vom Typ list")

    id_map, children_by_parent = build_tree(docs)  # type: ignore[arg-type]
    root_id = str(rem_root.get("documentRemToExportId") or export_meta.get("documentRemToExportId") or "")
    if not root_id:
        raise SystemExit("❌ documentRemToExportId fehlt")
    if root_id not in id_map:
        raise SystemExit(f"❌ Root-ID nicht in docs gefunden: {root_id}")

    export_date = str(rem_root.get("exportDate") or export_meta.get("exportDate") or "")
    kb_id = str(rem_root.get("knowledgebaseId") or export_meta.get("knowledgebaseId") or "")
    root_title = str(export_meta.get("root_title") or "")

    # Extract subtree
    nodes = iter_subtree(root_id=root_id, id_map=id_map, children_by_parent=children_by_parent)

    # Outputs
    nodes_out = out_dir / "remnote_extracted_nodes.jsonl"
    md_out = out_dir / "remnote_extracted_outline.md"
    report_out = out_dir / "remnote_extraction_report.md"

    safe_backup_existing(nodes_out)
    safe_backup_existing(md_out)
    safe_backup_existing(report_out)

    # Write JSONL + Markdown
    total = 0
    nonempty = 0
    md_lines: List[str] = []

    md_lines.append(f"# RemNote Export – {root_title or 'Export'}")
    md_lines.append("")
    md_lines.append(f"- Export-Datei: `{export_file.name}`")
    if export_date:
        md_lines.append(f"- exportDate: `{export_date}`")
    if kb_id:
        md_lines.append(f"- knowledgebaseId: `{kb_id}`")
    md_lines.append("")
    md_lines.append("## Outline")
    md_lines.append("")

    with open(nodes_out, "w", encoding="utf-8") as f_jsonl:
        for node, depth, path in nodes:
            total += 1
            node_id = str(node.get("_id") or "")
            parent_id = node.get("parent")
            parent_id = str(parent_id) if isinstance(parent_id, str) else None
            text = extract_text_from_key_field(node.get("key"))
            if text:
                nonempty += 1

            record = {
                "node_id": node_id,
                "parent_id": parent_id,
                "depth": depth,
                "path": path,
                "path_str": " > ".join(path),
                "text": text,
                "export": {
                    "file": str(export_file),
                    "exportDate": export_date,
                    "knowledgebaseId": kb_id,
                    "root_title": root_title,
                    "root_id": root_id,
                },
            }
            f_jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Markdown line (skip empty)
            if text:
                if depth == 0:
                    md_lines.append(f"- **{text}**")
                else:
                    indent = "  " * depth
                    md_lines.append(f"{indent}- {text}")

    md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    report = [
        "# RemNote Extraction Report",
        "",
        f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Quelle",
        "",
        f"- export_file: `{export_file}`",
        f"- exportDate: `{export_date}`",
        f"- knowledgebaseId: `{kb_id}`",
        f"- root_title: `{root_title}`",
        f"- root_id: `{root_id}`",
        "",
        "## Statistik",
        "",
        f"- nodes_total: {total}",
        f"- nodes_with_text: {nonempty}",
        "",
        "## Outputs",
        "",
        f"- `{nodes_out}`",
        f"- `{md_out}`",
        f"- `{report_out}`",
        "",
    ]
    report_out.write_text("\n".join(report), encoding="utf-8")

    print(f"✅ nodes: {nodes_out} ({total} Zeilen)")
    print(f"✅ md:    {md_out}")
    print(f"✅ report:{report_out}")


if __name__ == "__main__":
    main()


