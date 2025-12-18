#!/usr/bin/env bash
set -euo pipefail

# Uploadt ein zuvor erstelltes Bundle (tar/tar.gz) nach Google Drive via rclone.
#
# Usage:
#   ./MIGRATION_KIT/rclone_upload_bundle.sh /path/to/bundle.tar gdrive: Medexamenai_Migration_20251217
#
# Defaults:
#   remote = gdrive:
#   folder = Medexamenai_Migration

BUNDLE="${1:-}"
REMOTE="${2:-gdrive:}"
FOLDER="${3:-Medexamenai_Migration}"

if [[ -z "${BUNDLE}" ]]; then
  echo "Usage: $0 /path/to/bundle.tar [remote] [folder]"
  exit 1
fi

if [[ ! -f "${BUNDLE}" ]]; then
  echo "Bundle nicht gefunden: ${BUNDLE}"
  exit 2
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone ist nicht installiert. Bitte rclone installieren/konfigurieren."
  exit 3
fi

NAME="$(basename "${BUNDLE}")"
DEST="${REMOTE%/}/${FOLDER}/${NAME}"

echo "Upload: ${BUNDLE}"
echo "Nach:   ${DEST}"
echo "Hinweis: Das kann je nach Upload-Speed dauern."

# copyto: eine Datei → eine Datei
rclone copyto "${BUNDLE}" "${DEST}" --progress --check-first

# Optional: sha Datei daneben hochladen, falls vorhanden.
if [[ -f "${BUNDLE}.sha256" ]]; then
  rclone copyto "${BUNDLE}.sha256" "${DEST}.sha256" --progress --check-first
fi

echo "Fertig."


