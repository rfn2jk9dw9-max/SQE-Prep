#!/usr/bin/env python3
"""
sync_progress.py — Sync local progress.json corrections to the Hostinger server.

SAFE MODE (default): only updates sessions that exist in BOTH local and server
and have a score discrepancy. Never deletes server-only sessions.

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

    updated = inserted = 0

    # SAFE: only touch sessions that exist in BOTH and have wrong scores
    for dt, loc in local_by_dt.items():
        qs = loc.get('questions', [])
        loc_correct = sum(1 for q in qs if q.get('isCorrect'))
        total = len(qs)
        loc_pct = round(loc_correct / total * 100) if total else loc.get('percentage', 0)

        if dt in server_by_dt:
            srv = server_by_dt[dt]
            if abs(srv.get('percentage', 0) - loc_pct) > 0.5 or srv.get('correct', 0) != loc_correct:
                print(f"  Correcting {dt}: server={srv.get('correct')}/{srv.get('totalQ')} → local={loc_correct}/{total}")
                api('POST', {'delete_datetime': dt})
                payload = {
                    'datetime':     dt,
                    'paper':        loc.get('paper', srv.get('paper', 'FLK1')),
                    'percentage':   loc_pct,
                    'correct':      loc_correct,
                    'totalQ':       total,
                    'durationMode': loc.get('durationMode', srv.get('durationMode', 0)),
                    'subjects':     loc.get('subjects', srv.get('subjects', {})),
                    'questions':    qs,
                }
                api('POST', payload)
                updated += 1
            else:
                print(f"  OK {dt}: {loc_correct}/{total} matches server")
        else:
            # Local session not yet on server — insert it
            payload = {
                'datetime':     dt,
                'paper':        loc.get('paper', 'FLK1'),
                'percentage':   loc_pct,
                'correct':      loc_correct,
                'totalQ':       total,
                'durationMode': loc.get('durationMode', 0),
                'subjects':     loc.get('subjects', {}),
                'questions':    qs,
            }
            print(f"  Inserting {dt}: {loc_correct}/{total} = {loc_pct}%")
            api('POST', payload)
            inserted += 1

    # Report server-only sessions (preserved, not touched)
    server_only = [dt for dt in server_by_dt if dt not in local_by_dt]
    if server_only:
        print(f"\n  Server-only sessions (preserved): {len(server_only)}")
        for dt in server_only:
            s = server_by_dt[dt]
            print(f"    {dt}: {s.get('correct')}/{s.get('totalQ')}")

    print(f"\nDone — {updated} corrected, {inserted} inserted, {len(server_only)} server-only sessions preserved.")

if __name__ == '__main__':
    main()
