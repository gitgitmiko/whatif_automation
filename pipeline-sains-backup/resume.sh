#!/bin/bash
# Finishes a run whose images stopped at Google Flow's daily quota: the rest of the images, then the edit.
# Does nothing once final.mp4 exists, so running it twice is harmless.
cd "$(dirname "$0")"; slug="$1"; d=../runs/$slug
[ -f "$d/final.mp4" ] && { echo "$(date '+%F %H:%M') already done" >> "$d/resume.log"; exit 0; }
{ echo "RESUME $(date '+%F %H:%M')"; python3 images.py "$slug" && python3 edit.py "$slug"; echo "RESUME EXIT $? $(date +%H:%M)"; } >> "$d/resume.log" 2>&1
