#!/usr/bin/env bash
set -euo pipefail

CHECKSUM_FILE="${1:-}"
if [[ -z "${CHECKSUM_FILE}" ]]; then
  echo "Usage: $0 MIGRATION_KIT/checksums_<TS>.txt"
  exit 1
fi

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c "${CHECKSUM_FILE}"
else
  shasum -a 256 -c "${CHECKSUM_FILE}"
fi


