#!/usr/bin/env python3
"""
verify_conversion.py

Verifies that every JSON source file in the workspace has a corresponding
Markdown file under `_OUTPUT/md_converted/` (mirroring the directory
structure) and that every entry is present in the conversion inventory.
It also reports orphan Markdown files (without a JSON source).

The script writes a detailed report to
`_OUTPUT/md_converted/verification_report.md`
and prints the same information to stdout.

Only Python-standard-library modules are used.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Set

# --------------------------------------------------------------------------- #
#  Configuration & helpers
# --------------------------------------------------------------------------- #

ROOT_DIR = Path(__file__).resolve().parent  # Workspace root
OUTPUT_ROOT = ROOT_DIR / "_OUTPUT" / "md_converted"  # Markdown output root
INVENTORY_FILE = OUTPUT_ROOT / "inventory_all_qa.md"  # Master inventory


RELEVANT_DIRS = [
    "_EXTRACTED_FRAGEN",
    "_OUTPUT",
    "medexam_batch",
    "_BIBLIOTHEK",
]

EXCLUDE_PATTERNS = [
    ".mypy_cache",
    ".git",
    ".venv",
    ".embedding_cache",
    ".claude",
    "node_modules",
    "md_converted",
    ".backup",
    ".prewrite",
    ".checkpoint",
]


def _json_sources(root: Path) -> Iterable[Path]:
    """
    Yield only relevant *.json files (Q/A data, not cache files).
    """
    for rel_dir in RELEVANT_DIRS:
        search_dir = root / rel_dir
        if not search_dir.exists():
            continue

        for path in search_dir.rglob("*.json"):
            path_str = str(path)
            if any(excl in path_str for excl in EXCLUDE_PATTERNS):
                continue
            yield path


def _relative_to_root(path: Path) -> str:
    """Return a POSIX string of *path* relative to the workspace root."""
    return path.relative_to(ROOT_DIR).as_posix()


def _expected_md_rel(json_rel: str) -> str:
    """
    Given a JSON path relative to the workspace root, return the corresponding
    Markdown path relative to OUTPUT_ROOT.
    """
    return str(Path(json_rel).with_suffix(".md").as_posix())


def _parse_inventory(inv_file: Path) -> Set[str]:
    """
    Read *inv_file* and return a set with every JSON path (relative to the
    workspace root) that the inventory claims was processed.
    Lines of interest start with exactly:  'Original: '
    """
    if not inv_file.exists():
        return set()

    found: Set[str] = set()
    prefix = "Original:"
    with inv_file.open(encoding="utf-8") as fh:
        for line in fh:
            if line.startswith(prefix):
                _, raw_path = line.split(":", 1)
                raw_path = raw_path.strip()
                if not raw_path:
                    continue

                p = Path(raw_path)
                # Convert to a path relative to ROOT_DIR if possible
                if p.is_absolute():
                    try:
                        p = p.resolve().relative_to(ROOT_DIR)
                    except ValueError:
                        # Absolute path outside workspace – ignore
                        continue
                found.add(p.as_posix())
    return found


# --------------------------------------------------------------------------- #
#  Main verification logic
# --------------------------------------------------------------------------- #


def main() -> None:  # noqa: C901
    # --------------------------------------------------------------------- #
    # Discover JSON & Markdown files
    # --------------------------------------------------------------------- #
    json_files = list(_json_sources(ROOT_DIR))
    json_rel_set = {_relative_to_root(p) for p in json_files}

    md_files = list(OUTPUT_ROOT.rglob("*.md"))
    md_rel_set = {p.relative_to(OUTPUT_ROOT).as_posix() for p in md_files}

    # --------------------------------------------------------------------- #
    # Cross-checks
    # --------------------------------------------------------------------- #
    # JSON → expected Markdown mapping
    expected_md_map = {
        json_rel: _expected_md_rel(json_rel) for json_rel in json_rel_set
    }

    # (1) JSON without a matching Markdown file
    missing_md = [
        json_rel
        for json_rel, md_rel in expected_md_map.items()
        if md_rel not in md_rel_set
    ]

    # (2) Markdown files without a corresponding JSON source
    orphan_md = [
        md_rel
        for md_rel in md_rel_set
        if Path(md_rel).with_suffix(".json").as_posix() not in json_rel_set
    ]

    # (3) Inventory completeness
    inventory_json_set = _parse_inventory(INVENTORY_FILE)
    missing_from_inventory = sorted(json_rel_set - inventory_json_set)

    # --------------------------------------------------------------------- #
    # Assemble report
    # --------------------------------------------------------------------- #
    report_lines: list[str] = []
    report_lines.append("# Conversion Verification Report")
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    report_lines.append("")
    report_lines.append(f"- Total JSON files discovered: {len(json_rel_set):,}")
    report_lines.append(
        f"- Total Markdown files in `_OUTPUT/md_converted`: {len(md_rel_set):,}"
    )
    report_lines.append(f"- JSON files without matching Markdown: {len(missing_md):,}")
    report_lines.append(
        f"- Markdown files without corresponding JSON: {len(orphan_md):,}"
    )
    report_lines.append(
        f"- JSON files missing from inventory: {len(missing_from_inventory):,}"
    )
    report_lines.append("")

    def _section(title: str, items: list[str]) -> None:
        report_lines.append(f"## {title} ({len(items)})")
        if items:
            for item in sorted(items):
                report_lines.append(f"- {item}")
        else:
            report_lines.append("_None_")
        report_lines.append("")

    _section("JSON without Markdown", missing_md)
    _section("Markdown without JSON", orphan_md)
    _section("JSON missing from inventory_all_qa.md", missing_from_inventory)

    report_content = "\n".join(report_lines)

    # --------------------------------------------------------------------- #
    # Write report & output to console
    # --------------------------------------------------------------------- #
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_ROOT / "verification_report.md"
    report_path.write_text(report_content, encoding="utf-8")

    print(report_content)


# --------------------------------------------------------------------------- #
#  Script entry
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Cancelled by user")
