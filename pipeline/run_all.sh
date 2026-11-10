#!/bin/bash
# Everything after the verified script: storyboard, voice, images, edit. Stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")"; slug="$1"
echo "STAGE storyboard $(date +%H:%M)"; python3 storyboard.py "$slug"
echo "STAGE annotate $(date +%H:%M)"; python3 annotate.py "$slug"
echo "STAGE tts $(date +%H:%M)"; ../.venv/bin/python tts.py "$slug"
echo "STAGE images $(date +%H:%M)"; python3 images.py "$slug"
echo "STAGE thumbnail $(date +%H:%M)"; python3 thumbnail.py "$slug" || echo "thumbnail failed; the video keeps YouTube's own"
echo "STAGE clips $(date +%H:%M)"; python3 clips.py "$slug"
echo "STAGE edit $(date +%H:%M)"; python3 edit.py "$slug"
echo "STAGE ALLDONE $(date +%H:%M)"
