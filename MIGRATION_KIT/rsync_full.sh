#!/usr/bin/env bash
set -euo pipefail

SRC="/Users/user/Medexamenai/"
DST="${1:-}"

if [[ -z "${DST}" ]]; then
  echo "Usage: $0 /Volumes/EXTERNAL/Medexamenai/"
  exit 1
fi

rsync -a --info=progress2 "${SRC}" "${DST}"


