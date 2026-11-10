#!/bin/bash
# Finishes a run whose images stopped at Google Flow's daily quota: the rest of the images, the thumbnail, the edit,
# then marks it rendered so the dashboard and /api/ready see it. Does nothing once final.mp4 exists.
cd "$(dirname "$0")"; slug="$1"; d=../runs/$slug
[ -f "$d/final.mp4" ] && { echo "$(date '+%F %H:%M') already done" >> "$d/resume.log"; exit 0; }
{ echo "RESUME $(date '+%F %H:%M')"
  python3 images.py "$slug" && { python3 thumbnail.py "$slug" || echo "thumbnail failed; the video keeps YouTube's own"; } \
    && { python3 clips.py "$slug"; true; } \
    && python3 edit.py "$slug" \
    && python3 -c "import sys, server; from common import load; d = server.RUNS / sys.argv[1]; server.mark_rendered(sys.argv[1], d, load(d / 'script.json'))" "$slug"
  echo "RESUME EXIT $? $(date +%H:%M)"; } >> "$d/resume.log" 2>&1
