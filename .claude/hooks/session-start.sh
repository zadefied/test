#!/bin/bash
# Install the research pipeline's Python dependencies (yt-dlp, notebooklm-py).
set -euo pipefail

# Only needed in ephemeral cloud containers; local machines manage their own env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

pip install --quiet --upgrade -r "$CLAUDE_PROJECT_DIR/requirements.txt"
