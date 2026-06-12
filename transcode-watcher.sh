#!/usr/bin/env bash
# Host‑side watchdog that triggers the native transcoding pipeline.
# It watches the shared /app directory (mounted into the UI container) for trigger files.

SHARED_DIR="$(pwd)/app"
DB_PATH="${SHARED_DIR}/job_repo.db"

while true; do
  # ----- trigger all ------------------------------------------------------
  if [[ -f "${SHARED_DIR}/trigger_all" ]]; then
    echo "$(date) – trigger_all detected → running full pipeline" >> /tmp/transcode-watcher.log
    PYTHONPATH=. python main.py >> /tmp/transcode-watcher.log 2>&1
    rm -f "${SHARED_DIR}/trigger_all"
  fi

  # ----- trigger single ---------------------------------------------------
  for f in "${SHARED_DIR}"/trigger_*; do
    [[ -e "$f" ]] || continue
    # Extract the original path (underscores were used as slash placeholders)
    rel="${f#*trigger_}"
    target="${rel//_/\/}"   # turn underscores back into slashes
    echo "$(date) – trigger_one $target → processing single job" >> /tmp/transcode-watcher.log
    PYTHONPATH=. python main.py --path "$target" >> /tmp/transcode-watcher.log 2>&1
    rm -f "$f"
  done

  sleep 2
done
