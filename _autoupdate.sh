#!/bin/bash
# launchd entry point for the SQE1 site update (com.sqe1.autoupdate).
# 1. Only one update at a time: a second trigger waits for the first to finish.
# 2. Before running, makes sure iCloud hasn't moved project files back to the
#    cloud (that caused "Resource deadlock avoided" crashes in Nov 2026).
DIR="/Users/ghitab/Documents/Claude/Projects/Mission solicitor"
cd "$DIR" || { echo "✗ Project folder missing: $DIR"; exit 1; }
echo; echo "──── $(date '+%Y-%m-%d %H:%M:%S') auto-update triggered ────"

# --- lock -------------------------------------------------------------------
LOCK=/tmp/sqe1-autoupdate.lock
for i in $(seq 1 180); do                       # wait up to 30 min
  if mkdir "$LOCK" 2>/dev/null; then echo $$ > "$LOCK/pid"; break; fi
  old=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$old" ] && ! kill -0 "$old" 2>/dev/null; then rm -rf "$LOCK"; continue; fi
  [ "$i" -eq 1 ] && echo "  another update is running (pid $old), waiting..."
  sleep 10
done
[ -d "$LOCK" ] && [ "$(cat "$LOCK/pid" 2>/dev/null)" = "$$" ] || { echo "✗ Gave up waiting for the previous update"; exit 1; }
trap 'rm -rf "$LOCK"' EXIT

# --- iCloud preflight ---------------------------------------------------------
cloud_only() { find "$DIR" -type f -size +0 -exec stat -f '%b %N' {} + 2>/dev/null | awk '$1==0{ $1=""; print substr($0,2) }'; }
missing=$(cloud_only)
if [ -n "$missing" ]; then
  echo "  $(echo "$missing" | wc -l | tr -d ' ') file(s) are cloud-only; asking iCloud to download them..."
  brctl download "$DIR" >/dev/null 2>&1
  for i in $(seq 1 30); do                       # up to 5 min
    sleep 10; missing=$(cloud_only); [ -z "$missing" ] && break
  done
fi
if [ -n "$missing" ]; then
  echo "✗ iCloud has not downloaded these files, update skipped:"
  echo "$missing" | head -20 | sed 's/^/    /'
  echo "  Fix: run 'Download Project From iCloud.command' and make sure the folder is set to Keep Downloaded."
  exit 1
fi

# --- run --------------------------------------------------------------------
/usr/bin/python3 -u update_site.py
rc=$?
[ $rc -ne 0 ] && echo "✗ update_site.py exited with code $rc"
exit $rc
