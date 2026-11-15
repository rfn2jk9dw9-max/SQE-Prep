#!/bin/bash
# Installs (or reinstalls) the SQE1 auto-update job on this Mac:
# runs update_site.py every day at 07:00 and whenever a new test PDF lands.
SRC="/Users/ghitab/Documents/Claude/Projects/Mission solicitor/com.sqe1.autoupdate.plist"
DST="$HOME/Library/LaunchAgents/com.sqe1.autoupdate.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$SRC" "$DST"
launchctl bootout "gui/$(id -u)" "$DST" 2>/dev/null
if launchctl bootstrap "gui/$(id -u)" "$DST"; then
  echo "✓ Installed: SQE1 site updates daily at 07:00 and on new test PDFs."
  echo "  Log: Mission solicitor/autoupdate.log"
else
  echo "✗ Could not load the job — send this window's text to Claude."
fi
read -n 1 -s -r -p "Press any key to close"
