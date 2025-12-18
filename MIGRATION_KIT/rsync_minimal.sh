#!/usr/bin/env bash
set -euo pipefail

SRC="/Users/user/Medexamenai/"
DST="${1:-}"

if [[ -z "${DST}" ]]; then
  echo "Usage: $0 /Volumes/EXTERNAL/Medexamenai/"
  exit 1
fi

# Minimal: ohne Secrets und ohne sehr große Quellen/venv.
rsync -a --info=progress2 \
  --exclude ".env" \
  --exclude ".env.save" \
  --exclude "venv/" \
  --exclude "_FACT_CHECK_SOURCES/" \
  "${SRC}" "${DST}"


