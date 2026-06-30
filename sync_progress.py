#!/usr/bin/env python3
"""
sync_progress.py — Push corrected local progress.json to the Hostinger server.

The server uses INSERT IGNORE so stale entries won't auto-update.
This script: fetches server sessions → deletes any that differ from local → re-inserts corrected.

Run from Terminal:
    cd "/Users/ghitab/Documents/Claude/Projects/Mission solicitor"
    python3 sync_progress.py
"""

import json, urllib.request, urllib.error
from pathlib import Path

API = 'https://bidouillecode.dev/solicitor/progress.php'
LOCAL = Path(__file__).parent / 'progress.json'

def api(method, payload=None):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(API, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def main():
    local_sessions = json.loads(LOCAL.read_text(encoding='utf-8'))
    print(f"Local:  {len(local_sessions)} sessions")

    server_sessions = api('GET')
    print(f"Server: {len(server_sessions)} sessions")

    server_by_dt = {s['datetime']: s for s in server_sessions}
    local_by_dt  = {s['datetime']: s for s in local_sessions}

    updated = deleted = inserted = 0

    # Delete server sessions that differ from local (or are absent locally)
    for dt, srv in server_by_dt.items():
        if dt not in local_by_dt:
            print(f"  Deleting server-only session {dt}")
            api('POST', {'delete_datetime': dt})
            deleted += 1
        else:
            loc = local_by_dt[dt]
            loc_correct = sum(1 for q in loc.get('questions', []) if q.get('isCorrect'))
            loc_pct = round((loc_correct / len(loc['questions']) * 100)) if loc.get('questions') else loc.get('percentage', 0)
            if abs(srv.get('percentage', 0) - loc.get('percentage', loc_pct)) > 0.5 or \
               srv.get('correct', 0) != loc.get('correct', loc_correct):
                print(f"  Stale session {dt}: server={srv.get('correct')}/{srv.get('totalQ')} local={loc.get('correct', loc_correct)}/{len(loc.get('questions',[]))}, deleting")
                api('POST', {'delete_datetime': dt})
                deleted += 1

    # Re-fetch to see what's left
    server_sessions = api('GET')
    server_dts = {s['datetime'] for s in server_sessions}

    # Insert any local session not on server
    for s in local_sessions:
        dt = s['datetime']
        qs = s.get('questions', [])
        correct = sum(1 for q in qs if q.get('isCorrect'))
        total   = len(qs)
        pct     = round(correct / total * 100) if total else s.get('percentage', 0)

        if dt not in server_dts:
            payload = {
                'datetime':    dt,
                'paper':       s.get('paper', 'FLK1'),
                'percentage':  pct,
                'correct':     correct,
                'totalQ':      total,
                'durationMode': s.get('durationMode', 0),
                'subjects':    s.get('subjects', {}),
                'questions':   qs,
            }
            print(f"  Inserting {dt}: {correct}/{total} = {pct}%")
            api('POST', payload)
            inserted += 1

    print(f"\nDone — deleted {deleted}, inserted {inserted} sessions.")
    print("Dashboard will now show corrected scores.")

if __name__ == '__main__':
    main()
