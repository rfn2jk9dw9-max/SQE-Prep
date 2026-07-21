#!/usr/bin/env bash
# Resilient wrapper for update_site.py in the Cowork sandbox.
# The sandbox kills child processes when a bash call ends, which can happen
# mid cache-write and corrupt _parse_cache.json. This wrapper:
#   1. restores a known-good cache backup if the live cache is corrupt/empty
#   2. continuously snapshots the cache to .bak whenever it is valid JSON
#   3. runs update_site.py to make incremental parsing progress
cd "$(dirname "$0")" || exit 1
CACHE=_parse_cache.json
BAK=_parse_cache.bak

valid() { python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$1" 2>/dev/null; }

# 1. restore from backup if live cache is unusable but backup is good
if ! valid "$CACHE"; then
  if valid "$BAK"; then cp "$BAK" "$CACHE"; else echo '{}' > "$CACHE"; fi
fi

# 2. background snapshotter: keep a valid backup at all times
(
  while true; do
    if valid "$CACHE"; then
      n=$(python3 -c "import json;print(len(json.load(open('$CACHE'))))" 2>/dev/null)
      cp "$CACHE" "$BAK" 2>/dev/null
    fi
    sleep 2
  done
) &
SNAP=$!
trap "kill $SNAP 2>/dev/null" EXIT

# 3. run the real updater
python3 -u update_site.py
