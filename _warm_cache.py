#!/usr/bin/env python3
"""Warm _parse_cache.json within a time budget, saving atomically.
Exits 0 when all PDFs are cached, 3 when budget ran out (re-run me).
"""
import json, sys, time, os, tempfile
from pathlib import Path

BUDGET = 33  # seconds
START = time.time()

SCRIPT_DIR = Path(__file__).resolve().parent
TESTS_DIR = Path('/sessions/vigilant-youthful-mendel/mnt/Formation Solicitor/Tests')
CACHE_FILE = SCRIPT_DIR / '_parse_cache.json'

sys.path.insert(0, str(SCRIPT_DIR))
import parse_questions as pq

# Replicate dedup from parse_all
all_pdfs = sorted(TESTS_DIR.glob('*.pdf'))
seen = {}
for p in all_pdfs:
    key = pq._topic_key(p.stem)
    if key not in seen or p.stat().st_mtime > seen[key].stat().st_mtime:
        seen[key] = p
pdfs = sorted(seen.values())

cache = {}
if CACHE_FILE.exists():
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding='utf-8'))
    except Exception:
        cache = {}

def save():
    fd, tmp = tempfile.mkstemp(dir=str(SCRIPT_DIR), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, str(CACHE_FILE))

remaining = [p for p in pdfs
             if not (cache.get(str(p)) and abs(cache[str(p)].get('mtime', 0) - p.stat().st_mtime) < 1.0)]
print(f'{len(pdfs)} unique topics, {len(remaining)} to parse')

for p in remaining:
    if time.time() - START > BUDGET:
        save()
        print(f'BUDGET reached, cache saved ({len(cache)} entries)')
        sys.exit(3)
    subject, paper = pq.subject_from_filename(p.name)
    if p.stem.upper().startswith('SLK'):
        qs = pq.parse_canvas_pdf(str(p), subject, paper)
    else:
        qs = pq.parse_pdf(str(p), subject, paper)
    cache[str(p)] = {'mtime': p.stat().st_mtime, 'questions': qs}
    save()
    print(f'  {len(qs):3d} q  parsed  {p.name}  [{time.time()-START:.0f}s]')

save()
print(f'ALL CACHED ({len(cache)} entries)')
