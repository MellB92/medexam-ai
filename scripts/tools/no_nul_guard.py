"""Fail-fast guard against NUL bytes in source files.

Python cannot import/compile files containing NUL (\x00) bytes. This guard must run
*before* py_compile.

Usage:
  python3 scripts/tools/no_nul_guard.py path1 path2 ...

Supports simple glob patterns.
"""

from __future__ import annotations

import sys
from pathlib import Path


def iter_paths(args: list[str]):
    for a in args:
        p = Path(a)
        # naive glob support
        if any(ch in a for ch in ["*", "?", "[", "]"]):
            for m in Path().glob(a):
                if m.is_file():
                    yield m
        else:
            yield p


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python3 no_nul_guard.py <path/glob> [<path/glob> ...]", file=sys.stderr)
        return 2

    bad = []
    checked = 0
    for p in iter_paths(argv[1:]):
        if not p.exists():
            print(f"[no_nul_guard] WARN: missing path: {p}", file=sys.stderr)
            continue
        if not p.is_file():
            continue
        checked += 1
        b = p.read_bytes()
        if b"\x00" in b:
            bad.append(p)

    if bad:
        print("[no_nul_guard] ERROR: NUL bytes found in:", file=sys.stderr)
        for p in bad:
            print(f"- {p}", file=sys.stderr)
        return 1

    print(f"[no_nul_guard] OK: checked {checked} file(s), no NUL bytes found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
