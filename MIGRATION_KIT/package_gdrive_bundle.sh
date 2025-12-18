#!/usr/bin/env bash
set -euo pipefail

# Erstellt ein einzelnes Archiv (tar), das sich gut für Uploads eignet.
# Default: FULL (inkl. _FACT_CHECK_SOURCES), aber OHNE .git/backups/dropbox_import/venv/.env
#
# Usage:
#   ./MIGRATION_KIT/package_gdrive_bundle.sh            # full bundle (no compression)
#   ./MIGRATION_KIT/package_gdrive_bundle.sh --slim     # exclude _FACT_CHECK_SOURCES
#   ./MIGRATION_KIT/package_gdrive_bundle.sh --gzip     # additionally gzip (-1)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${ROOT}/_OUTPUT/migration_bundles"
MODE="full"
DO_GZIP="0"

for arg in "$@"; do
  case "${arg}" in
    --slim) MODE="slim" ;;
    --gzip) DO_GZIP="1" ;;
    *) echo "Unbekanntes Argument: ${arg}" && exit 2 ;;
  esac
done

mkdir -p "${OUT_DIR}"

OUT_TAR="${OUT_DIR}/Medexamenai_migration_${MODE}_${TS}.tar"

echo "Erstelle Bundle: ${OUT_TAR}"
echo "Mode: ${MODE} (slim = ohne _FACT_CHECK_SOURCES)"
echo "Hinweis: .env/.env.save werden NICHT gepackt (Secrets)."

# BSD tar (macOS) versteht --exclude.
tar -cf "${OUT_TAR}" \
  --exclude ".git" \
  --exclude "dropbox_import" \
  --exclude "backups" \
  --exclude "venv" \
  --exclude ".venv" \
  --exclude ".env" \
  --exclude ".env.save" \
  --exclude "nohup.out" \
  --exclude ".DS_Store" \
  --exclude "*/.DS_Store" \
  --exclude "__pycache__" \
  --exclude "*/__pycache__" \
  --exclude "*.pyc" \
  --exclude "Gold Standards*.zip" \
  -C "${ROOT}" .

if [[ "${MODE}" == "slim" ]]; then
  # Entferne _FACT_CHECK_SOURCES nachträglich aus dem tar, falls es doch drin wäre
  # (sicherer: tar neu bauen). Für Einfachheit: neues tar bauen, wenn slim.
  TMP_TAR="${OUT_TAR}.tmp"
  mv "${OUT_TAR}" "${TMP_TAR}"
  tar -cf "${OUT_TAR}" \
    --exclude "_FACT_CHECK_SOURCES" \
    -C "${ROOT}" \
    --exclude ".git" \
    --exclude "dropbox_import" \
    --exclude "backups" \
    --exclude "venv" \
    --exclude ".venv" \
    --exclude ".env" \
    --exclude ".env.save" \
    --exclude "nohup.out" \
    --exclude ".DS_Store" \
    --exclude "*/.DS_Store" \
    --exclude "__pycache__" \
    --exclude "*/__pycache__" \
    --exclude "*.pyc" \
    --exclude "Gold Standards*.zip" \
    .
  rm -f "${TMP_TAR}"
fi

# SHA256 schreiben (für späteren Verify)
SHA_FILE="${OUT_TAR}.sha256"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${OUT_TAR}" > "${SHA_FILE}"
else
  shasum -a 256 "${OUT_TAR}" > "${SHA_FILE}"
fi

if [[ "${DO_GZIP}" == "1" ]]; then
  echo "gzip -1 (schnell, geringe Kompression)…"
  gzip -1 "${OUT_TAR}"
  OUT_TAR="${OUT_TAR}.gz"
  # checksum für gz
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${OUT_TAR}" > "${OUT_TAR}.sha256"
  else
    shasum -a 256 "${OUT_TAR}" > "${OUT_TAR}.sha256"
  fi
fi

ls -lh "${OUT_TAR}" || true
echo "Fertig."
echo "Bundle: ${OUT_TAR}"


