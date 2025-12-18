#!/usr/bin/env python3
"""
Merge regenerated answers into a main dataset by exact question string.

Use-case:
- Targeted re-generation (e.g. "68 wrong answers") where questions already exist
  in `_OUTPUT/evidenz_antworten.json` and only `antwort` should be replaced.

Safety:
- Creates a timestamped backup before writing.
- By default, only replaces existing questions (does NOT add new entries).
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_question(entry: Dict[str, Any]) -> str:
    return (entry.get("frage") or entry.get("question") or "").strip()


def _extract_answer(entry: Dict[str, Any]) -> str:
    return (entry.get("antwort") or entry.get("answer") or "").strip()


def _load_targets(path: Path) -> Set[str]:
    data = _load_json(path)
    targets: Set[str] = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                q = _extract_question(item)
            else:
                q = str(item).strip()
            if q:
                targets.add(q)
    elif isinstance(data, dict):
        # Best effort: accept {"questions": [...]} style
        maybe_list = data.get("questions") or data.get("items") or data.get("data")
        if isinstance(maybe_list, list):
            for item in maybe_list:
                if isinstance(item, dict):
                    q = _extract_question(item)
                else:
                    q = str(item).strip()
                if q:
                    targets.add(q)
    return targets


def _index_main(main_data: List[Dict[str, Any]]) -> Dict[str, int]:
    index: Dict[str, int] = {}
    for i, item in enumerate(main_data):
        q = _extract_question(item)
        if q:
            index[q] = i
    return index


def _merge(
    *,
    main_data: List[Dict[str, Any]],
    regen_data: List[Dict[str, Any]],
    targets: Optional[Set[str]],
    min_answer_len: int,
    add_missing: bool,
    regen_source: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    main_index = _index_main(main_data)
    regen_index: Dict[str, Dict[str, Any]] = {}
    for item in regen_data:
        if not isinstance(item, dict):
            continue
        q = _extract_question(item)
        if q:
            regen_index[q] = item

    replaced: List[Dict[str, Any]] = []
    skipped_short = 0
    skipped_not_in_targets = 0
    missing_in_main = 0
    missing_in_regen = 0

    now = datetime.now().isoformat()

    iter_targets: Iterable[str]
    if targets is None:
        iter_targets = regen_index.keys()
    else:
        iter_targets = targets

    for q in iter_targets:
        regen_item = regen_index.get(q)
        if regen_item is None:
            missing_in_regen += 1
            continue

        answer = _extract_answer(regen_item)
        if len(answer) < min_answer_len:
            skipped_short += 1
            continue

        idx = main_index.get(q)
        if idx is None:
            missing_in_main += 1
            if not add_missing:
                continue
            main_data.append(
                {
                    "frage": q,
                    "source_file": regen_item.get("source_file", ""),
                    "antwort": answer,
                    "regenerated_at": now,
                    "regen_model": regen_item.get("model")
                    or regen_item.get("model_used")
                    or regen_item.get("model_name")
                    or "",
                    "regen_source": regen_source,
                }
            )
            continue

        if targets is not None and q not in targets:
            skipped_not_in_targets += 1
            continue

        old_answer = (main_data[idx].get("antwort") or "").strip()
        main_data[idx]["antwort"] = answer
        main_data[idx]["regenerated_at"] = now
        main_data[idx]["regen_model"] = (
            regen_item.get("model")
            or regen_item.get("model_used")
            or regen_item.get("model_name")
            or ""
        )
        main_data[idx]["regen_source"] = regen_source

        replaced.append(
            {
                "index": idx,
                "frage": q,
                "old_answer": old_answer,
                "new_answer": answer,
                "score_before": regen_item.get("score_before"),
                "fehler_before": regen_item.get("fehler_before"),
            }
        )

    summary = {
        "timestamp": now,
        "main_entries": len(main_data),
        "regen_entries": len(regen_data),
        "targets_count": len(targets) if targets is not None else None,
        "replaced": len(replaced),
        "skipped_short": skipped_short,
        "missing_in_main": missing_in_main,
        "missing_in_regen": missing_in_regen,
        "skipped_not_in_targets": skipped_not_in_targets,
    }

    return replaced, summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge regenerated answers into main JSON by exact question string"
    )
    parser.add_argument(
        "--main",
        default="_OUTPUT/evidenz_antworten.json",
        help="Main JSON file (list of Q&A dicts)",
    )
    parser.add_argument(
        "--regen",
        required=True,
        help="Regen answers JSON file (list of dicts with frage+antwort)",
    )
    parser.add_argument(
        "--targets",
        default=None,
        help="Optional JSON list/dict containing the questions to replace (exact match)",
    )
    parser.add_argument(
        "--min-answer-len",
        type=int,
        default=50,
        help="Skip regen answers shorter than this",
    )
    parser.add_argument(
        "--add-missing",
        action="store_true",
        help="If a regen question is not in main, append it (default: false)",
    )
    parser.add_argument(
        "--backup-dir",
        default="_OUTPUT/backups",
        help="Where to write the backup before merging",
    )
    parser.add_argument(
        "--write-fixed",
        default="_OUTPUT/fixed_regen_merge.json",
        help="Write replaced items (old+new) here",
    )
    parser.add_argument(
        "--write-summary",
        default="_OUTPUT/fixed_regen_merge_summary.json",
        help="Write merge summary here",
    )
    args = parser.parse_args()

    main_path = Path(args.main)
    regen_path = Path(args.regen)
    if not main_path.exists():
        raise SystemExit(f"Main file not found: {main_path}")
    if not regen_path.exists():
        raise SystemExit(f"Regen file not found: {regen_path}")

    targets: Optional[Set[str]] = None
    if args.targets:
        targets = _load_targets(Path(args.targets))
        if not targets:
            raise SystemExit(f"No targets loaded from: {args.targets}")

    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{main_path.stem}_pre_regen_merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    print(f"📦 Backup: {backup_path}")
    shutil.copy(main_path, backup_path)

    main_data = _load_json(main_path)
    regen_data = _load_json(regen_path)
    if not isinstance(main_data, list):
        raise SystemExit("Main JSON must be a list")
    if not isinstance(regen_data, list):
        raise SystemExit("Regen JSON must be a list")

    replaced, summary = _merge(
        main_data=main_data,
        regen_data=regen_data,
        targets=targets,
        min_answer_len=args.min_answer_len,
        add_missing=args.add_missing,
        regen_source=regen_path.name,
    )

    _dump_json(Path(args.write_fixed), replaced)
    _dump_json(Path(args.write_summary), summary)
    _dump_json(main_path, main_data)

    print("\n=== Merge Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\n✅ Wrote main: {main_path}")
    print(f"✅ Wrote fixed: {args.write_fixed}")
    print(f"✅ Wrote summary: {args.write_summary}")
    print(f"✅ Backup: {backup_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
