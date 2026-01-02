#!/usr/bin/env python3
"""
Run OpenAI Batch jobs from a manifest (sequentially) and download outputs.

Why:
- OpenAI has an organization-wide enqueued-token limit for batch jobs.
- We generate split batch input parts (see build_openai_batch_all_materials.py --split-max-enqueued-tokens).
- Running parts sequentially avoids hitting the enqueued limit.

Inputs:
- manifest JSON (default: _OUTPUT/openai_batch_all/openai_batch_input_manifest.json)

Outputs:
- per-part folder under <run-dir>/partXYZ/ with:
  - file_upload.json
  - batch_create.json
  - batch_status.json (last)
  - output.jsonl (if completed)
  - error.jsonl (if provided)
- merged output: _OUTPUT/openai_batch_all/openai_batch_output.jsonl

Auth:
- reads OPENAI_API_KEY from environment.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class OpenAIHttp:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base = "https://api.openai.com/v1"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def upload_batch_file(self, *, jsonl_path: Path) -> Dict[str, Any]:
        with jsonl_path.open("rb") as f:
            files = {"file": (jsonl_path.name, f, "application/jsonl")}
            data = {"purpose": "batch"}
            r = requests.post(f"{self.base}/files", headers=self.headers, files=files, data=data, timeout=300)
        r.raise_for_status()
        return r.json()

    def create_batch(self, *, input_file_id: str, endpoint: str, completion_window: str) -> Dict[str, Any]:
        payload = {"input_file_id": input_file_id, "endpoint": endpoint, "completion_window": completion_window}
        r = requests.post(
            f"{self.base}/batches",
            headers={**self.headers, "Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        return r.json()

    def get_batch(self, batch_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/batches/{batch_id}", headers=self.headers, timeout=120)
        r.raise_for_status()
        return r.json()

    def download_file_content(self, file_id: str) -> str:
        r = requests.get(f"{self.base}/files/{file_id}/content", headers=self.headers, timeout=300)
        r.raise_for_status()
        return r.text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--manifest",
        default="_OUTPUT/openai_batch_all/openai_batch_input_manifest.json",
        help="Split manifest from build_openai_batch_all_materials.py",
    )
    ap.add_argument("--run-dir", default="_OUTPUT/openai_batch_all/runs", help="Where to store per-part artifacts")
    ap.add_argument("--endpoint", default="/v1/responses", help="Batch endpoint")
    ap.add_argument("--completion-window", default="24h", help="OpenAI batch completion window")
    ap.add_argument("--poll-seconds", type=int, default=20, help="Polling interval")
    ap.add_argument("--resume", action="store_true", help="Skip parts that already have output.jsonl")
    args = ap.parse_args()

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY fehlt in der Umgebung.")

    repo_root = Path(".")
    manifest_path = repo_root / args.manifest
    run_dir = repo_root / args.run_dir
    m = _load_json(manifest_path)
    parts: List[Dict[str, Any]] = list(m.get("parts") or [])
    if not parts:
        raise SystemExit(f"Keine parts in manifest: {manifest_path}")

    client = OpenAIHttp(api_key)

    merged_out = repo_root / "_OUTPUT/openai_batch_all/openai_batch_output.jsonl"
    merged_lines: List[str] = []

    for p in parts:
        part_no = int(p.get("part") or 0)
        part_rel = str(p.get("path") or "")
        if not part_no or not part_rel:
            continue

        jsonl_path = repo_root / part_rel
        if not jsonl_path.exists():
            raise SystemExit(f"Part file missing: {jsonl_path}")

        part_dir = run_dir / f"part{part_no:03d}"
        part_dir.mkdir(parents=True, exist_ok=True)

        out_jsonl = part_dir / "output.jsonl"
        if args.resume and out_jsonl.exists() and out_jsonl.stat().st_size > 0:
            # Load into merged output later
            merged_lines.extend(out_jsonl.read_text(encoding="utf-8").splitlines())
            print(f"⏭️  part{part_no:03d}: resume (output exists)")
            continue

        print(f"⬆️  part{part_no:03d}: upload {jsonl_path.name} ...")
        upload = client.upload_batch_file(jsonl_path=jsonl_path)
        _save_json(part_dir / "file_upload.json", upload)
        file_id = str(upload.get("id") or "")
        if not file_id:
            raise SystemExit(f"Upload fehlgeschlagen: kein file_id (part{part_no:03d})")

        print(f"🧾 part{part_no:03d}: create batch ...")
        batch = client.create_batch(
            input_file_id=file_id, endpoint=args.endpoint, completion_window=args.completion_window
        )
        _save_json(part_dir / "batch_create.json", batch)
        batch_id = str(batch.get("id") or "")
        if not batch_id:
            raise SystemExit(f"Batch create fehlgeschlagen: kein batch_id (part{part_no:03d})")

        # Poll
        while True:
            status = client.get_batch(batch_id)
            _save_json(part_dir / "batch_status.json", status)
            st = str(status.get("status") or "")
            if st in {"completed", "failed", "expired", "cancelled"}:
                break
            print(f"⏳ part{part_no:03d}: status={st} ...")
            time.sleep(max(5, int(args.poll_seconds)))

        st = str(status.get("status") or "")
        if st != "completed":
            # Try to show first error line in status
            errs = (status.get("errors") or {}).get("data") or []
            msg = ""
            if isinstance(errs, list) and errs:
                msg = str((errs[0] or {}).get("message") or "")
            raise SystemExit(f"Batch part{part_no:03d} failed: status={st} {msg[:200]}")

        counts = status.get("request_counts") or {}
        total = int(counts.get("total") or 0)
        completed = int(counts.get("completed") or 0)
        failed = int(counts.get("failed") or 0)

        out_id = status.get("output_file_id")
        err_id = status.get("error_file_id")
        if out_id:
            text = client.download_file_content(str(out_id))
            _save_text(out_jsonl, text)
            merged_lines.extend(text.splitlines())
            print(f"✅ part{part_no:03d}: downloaded output ({len(text.splitlines())} lines)")
        if err_id:
            err_text = client.download_file_content(str(err_id))
            _save_text(part_dir / "error.jsonl", err_text)
            # Fail fast if the whole part failed (no outputs possible).
            if total > 0 and failed == total and completed == 0:
                first = (err_text.splitlines() or [""])[0]
                raise SystemExit(f"Batch part{part_no:03d}: all requests failed. First error: {first[:240]}")

    merged_out.parent.mkdir(parents=True, exist_ok=True)
    merged_out.write_text("\n".join([ln for ln in merged_lines if ln.strip()]) + "\n", encoding="utf-8")
    print(f"📦 merged output: {merged_out} (lines={len([ln for ln in merged_lines if ln.strip()])})")


if __name__ == "__main__":
    main()
