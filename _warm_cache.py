#!/usr/bin/env python3
"""Warm _parse_cache.json within a time budget, saving atomically.
Exits 0 when all PDFs are cached, 3 when budget ran out (re-run me).
"""
import json, sys, time, os, tempfile
from pathlib import Path

BUDGET = 33  # seconds
START = time.time()

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_FILE = SCRIPT_DIR / '_parse_cache.json'


def _find_tests_dir():
    """Locate the Tests folder on the Mac OR inside any Cowork sandbox session.
    Session mount names change every run, so probe dynamically instead of
    hardcoding a path."""
    candidates = [
        Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/Tests',
    ]
    sessions_root = Path('/sessions')
    if sessions_root.exists():
        try:
            for session in sessions_root.iterdir():
                candidates.append(session / 'mnt' / 'Formation Solicitor' / 'Tests')
        except PermissionError:
            pass
    for c in candidates:
        try:
            if c.exists():
                return c
        except PermissionError:
            continue
    return candidates[0]


TESTS_DIR = _find_tests_dir()

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

def _is_cached(p):
    """Cache hit if keyed by filename and file size matches (mtime fallback for
    legacy entries).  Mirrors parse_questions.parse_all validation."""
    c = cache.get(p.name)
    if not c:
        return False
    size = p.stat().st_size
    if c.get('size') is not None:
        return c.get('size') == size
    return abs(c.get('mtime', 0) - p.stat().st_mtime) < 1.0


remaining = [p for p in pdfs if not _is_cached(p)]
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
    st = p.stat()
    cache[p.name] = {'mtime': st.st_mtime, 'size': st.st_size, 'questions': qs}
    save()
    print(f'  {len(qs):3d} q  parsed  {p.name}  [{time.time()-START:.0f}s]')

save()
print(f'ALL CACHED ({len(cache)} entries)')
