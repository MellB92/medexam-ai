#!/usr/bin/env python3
"""
Aufgabe 2 (v2): Report zur Deck-Filterung (Vergleich v1 vs v2).

Outputs:
- `_OUTPUT/deck_filter_report_v2.md`
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


def apkg_counts(apkg_path: Path) -> Tuple[int, int]:
    """Liest Notes/Cards Counts aus einem .apkg (collection.anki21/anki2)."""
    if not apkg_path.exists():
        return (0, 0)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(apkg_path, "r") as z:
            z.extractall(tmp_path)
        db = tmp_path / "collection.anki21"
        if not db.exists():
            db = tmp_path / "collection.anki2"
        if not db.exists():
            return (0, 0)
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM notes")
        notes = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM cards")
        cards = int(cur.fetchone()[0])
        conn.close()
        return (notes, cards)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def categorize_tag(tag: str) -> str:
    t = (tag or "").lower()
    if "strahlenschutz" in t:
        return "strahlenschutz"
    if "pharmakologie" in t or "pharmakologie_dellas" in t:
        return "pharmakologie"
    if "rechtsmedizin" in t:
        return "rechtsmedizin"
    if "notfallmedizin" in t:
        return "notfallmedizin"
    if "hygiene" in t or "infektionsschutzgesetz" in t or "ifsg" in t:
        return "hygiene"
    if "arbeitsmedizin" in t:
        return "arbeitsmedizin"
    return "rest"


def summarize_matched(matched: dict) -> Dict[str, Any]:
    include = matched.get("include_tags") or []
    conf = matched.get("match_confidence") or {}
    meta = matched.get("match_meta") or {}

    cat = Counter()
    for t in include:
        cat[categorize_tag(t)] += 1

    # top by confidence
    top = sorted(include, key=lambda x: (-float(conf.get(x, 0.0) or 0.0), x))[:50]
    top_rows = []
    for t in top:
        top_rows.append(
            {
                "tag": t,
                "confidence": conf.get(t),
                "matched_term": (meta.get(t) or {}).get("matched_term"),
                "match_type": (meta.get(t) or {}).get("match_type"),
            }
        )

    return {
        "include_count": len(include),
        "by_category": dict(cat),
        "top_rows": top_rows,
    }


def main() -> None:
    repo_root = Path(__file__).parent.parent
    out_path = repo_root / "_OUTPUT" / "deck_filter_report_v2.md"

    # Inputs
    v1_ank = load_json(repo_root / "_OUTPUT" / "ankizin_matched_tags.json")
    v1_del = load_json(repo_root / "_OUTPUT" / "dellas_matched_tags.json")
    v2_ank = load_json(repo_root / "_OUTPUT" / "ankizin_matched_tags_v2.json")
    v2_del = load_json(repo_root / "_OUTPUT" / "dellas_matched_tags_v2.json")

    apkg_v1_ank = repo_root / "_OUTPUT" / "Ankizin_KP_Muenster_filtered.apkg"
    apkg_v1_del = repo_root / "_OUTPUT" / "Dellas_KP_Muenster_filtered.apkg"
    apkg_v2_ank = repo_root / "_OUTPUT" / "Ankizin_KP_Muenster_filtered_v2.apkg"
    apkg_v2_del = repo_root / "_OUTPUT" / "Dellas_KP_Muenster_filtered_v2.apkg"

    v1_ank_notes, v1_ank_cards = apkg_counts(apkg_v1_ank)
    v1_del_notes, v1_del_cards = apkg_counts(apkg_v1_del)
    v2_ank_notes, v2_ank_cards = apkg_counts(apkg_v2_ank)
    v2_del_notes, v2_del_cards = apkg_counts(apkg_v2_del)

    sum_v1_ank = summarize_matched(v1_ank)
    sum_v1_del = summarize_matched(v1_del)
    sum_v2_ank = summarize_matched(v2_ank)
    sum_v2_del = summarize_matched(v2_del)

    def mb(p: Path) -> str:
        return f"{p.stat().st_size/1024/1024:.2f} MB" if p.exists() else "n/a"

    lines: list[str] = []
    lines.append("# Deck Filter Report v2 (KP Münster)\n\n")
    lines.append(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    lines.append("## Vergleich v1 vs v2 (High-Level)\n\n")
    lines.append("| Deck | v1 Tags | v2 Tags | v1 Notes | v2 Notes | v1 Cards | v2 Cards | v1 Size | v2 Size |\n")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    lines.append(
        f"| Ankizin | {sum_v1_ank['include_count']} | {sum_v2_ank['include_count']} | {v1_ank_notes} | {v2_ank_notes} | {v1_ank_cards} | {v2_ank_cards} | {mb(apkg_v1_ank)} | {mb(apkg_v2_ank)} |\n"
    )
    lines.append(
        f"| Dellas | {sum_v1_del['include_count']} | {sum_v2_del['include_count']} | {v1_del_notes} | {v2_del_notes} | {v1_del_cards} | {v2_del_cards} | {mb(apkg_v1_del)} | {mb(apkg_v2_del)} |\n"
    )

    lines.append("\n---\n")
    lines.append("## v2 Tag-Verteilung nach Kategorie (Ankizin)\n\n")
    for k, v in sorted(sum_v2_ank["by_category"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- **{k}**: {v}\n")

    lines.append("\n## v2 Tag-Verteilung nach Kategorie (Dellas)\n\n")
    for k, v in sorted(sum_v2_del["by_category"].items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- **{k}**: {v}\n")

    lines.append("\n---\n")
    lines.append("## v2 Included Tags (Top 50) – Ankizin\n\n")
    lines.append("| Tag | confidence | matched_term | match_type |\n")
    lines.append("|---|---:|---|---|\n")
    for r in sum_v2_ank["top_rows"]:
        lines.append(f"| `{r['tag']}` | {r.get('confidence','')} | {r.get('matched_term','')} | {r.get('match_type','')} |\n")

    lines.append("\n## v2 Included Tags (Top 50) – Dellas\n\n")
    lines.append("| Tag | confidence | matched_term | match_type |\n")
    lines.append("|---|---:|---|---|\n")
    for r in sum_v2_del["top_rows"]:
        lines.append(f"| `{r['tag']}` | {r.get('confidence','')} | {r.get('matched_term','')} | {r.get('match_type','')} |\n")

    lines.append("\n---\n")
    lines.append("## Hinweise zur v2-Qualität\n\n")
    lines.append("- **Matching ist strikt** (exakte/Boundary Matches; keine fuzzy Similarity).\n")
    lines.append("- **Meta-Tags** (z.B. `z_Credit`, `!Delete`, `!Missing`) werden ausgeschlossen.\n")
    lines.append("- **Ankizin-Scoping:** bevorzugt `Kenntnisprüfung`-Tags; ohne KP-Signal werden nur Querschnitt-Fächer (Strahlenschutz/Rechtsmedizin/Notfall/Hygiene/Arbeitsmedizin) zugelassen.\n")
    lines.append("- **Dellas-Scoping:** nur Kapitel/Bibliothek/Wirkstoff-Tags; Matching ohne triviales `pharmakologie`.\n")

    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"✅ Report erstellt: {out_path}")


if __name__ == "__main__":
    main()


