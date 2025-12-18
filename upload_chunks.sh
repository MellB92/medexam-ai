#!/bin/bash

# Configuration
SOURCE_DIR="dropbox_import"
DEST_REMOTE="gdrive:/Dropbox_Import_2025-12-12/Chunks"
LOG_FILE="upload_chunks.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Starting Upload of Chunks at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Create destination folder (just in case)
rclone mkdir "$DEST_REMOTE"

# Loop through all part files
for file in "$SOURCE_DIR"/AMIR_part_*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "----------------------------------------" | tee -a "$LOG_FILE"
        echo "Uploading $filename..." | tee -a "$LOG_FILE"
        
        # Upload with retries
        # -P shows progress in terminal, but for background/logging we verify exit code
        if rclone copy "$file" "$DEST_REMOTE" --verbose --transfers 1 --retries 5 >> "$LOG_FILE" 2>&1; then
            echo "✅ SUCCESS: $filename uploaded." | tee -a "$LOG_FILE"
        else
            echo "❌ FAILED: $filename could not be uploaded after retries." | tee -a "$LOG_FILE"
            echo "Stopping script. Please check internet and run again." | tee -a "$LOG_FILE"
            exit 1
        fi
    fi
done

echo "========================================" | tee -a "$LOG_FILE"
echo "All chunks finished at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
