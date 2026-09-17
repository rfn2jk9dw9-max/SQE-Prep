"""
Per-chapter answer record from the COLP topic tests, for the revision schedule.

SQE1_COLP_Revision.html ranks final-phase revisits (from 16 Dec) by how often
each chapter is answered wrongly. Two sources feed that ranking:

  * mock exam sessions — fetched live by the page from progress.php, so they
    count the moment a session is saved;
  * COLP topic tests (the H5P/Canvas PDFs in the Tests folder) — the page
    cannot read those, so this module turns them into a list of attempts and
    update_site.py writes it into the page on every run.

The page does the weighting itself, against the day it is opened: recent
answers count more than old ones, so the ranking moves as results come in.
This module only records what happened — one row per attempt:

    [chapter code, date, questions answered, answered wrongly, retake flag]

Sources, in order of preference:
  * colp_grades.json — every graded attempt per chapter test, exported from
    the Canvas grades page (covers the 10/10 attempts that were never saved
    as PDFs). Used for every chapter it covers.
  * chapter-test PDFs — only for chapters Canvas has no record of.
  * Progress Taster / Test PDFs — Canvas only has their totals, so the
    per-chapter split always comes from the PDF.

Retakes reuse the same questions, so they are flagged and the page gives them
less weight than a first attempt.
"""
import datetime
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

MODULE_PREFIX = {1: "CONT", 2: "TORT", 3: "COND", 4: "LAND", 5: "CRML",
                 6: "TRUS", 7: "BUS", 8: "DISP", 9: "CRMP", 10: "SERV",
                 11: "SYS", 12: "PROP", 13: "WILL"}

_NUM_RE = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})(?!\d)")
MARK_RE = re.compile(r"/\*TOPIC_TEST_STATS_START\*/.*?/\*TOPIC_TEST_STATS_END\*/", re.S)


def code_from_chapter(num: str, valid: set) -> Optional[str]:
    """'8.12' -> 'DISP8.12' (only if the COLP calendar knows that module)."""
    m = _NUM_RE.search(num or "")
    if not m or int(m.group(1)) not in MODULE_PREFIX:
        return None
    code = "%s%d.%d" % (MODULE_PREFIX[int(m.group(1))], int(m.group(1)), int(m.group(2)))
    return code if code in valid else None


def code_from_filename(name: str, valid: set) -> Optional[str]:
    # Filenames spell the prefix inconsistently ("CRM 5.3", "WILLS 13.5",
    # "ADISP8.12", "10.2 v2") — the module NUMBER is reliable, the letters are not.
    return code_from_chapter(name, valid)


def _stem(t: str) -> str:
    return re.sub(r"\W+", " ", (t or "").lower()).strip()[:80]


def load_canvas_grades(grades_file: Path, valid: set) -> Dict[str, List[list]]:
    """code -> [[code, date, points, wrong, retake], ...] from colp_grades.json."""
    out = {}
    p = Path(grades_file)
    if not p.exists():
        return out
    data = json.loads(p.read_text(encoding="utf-8"))
    for a in data.get("assignments", []):
        m = re.match(r"\s*([A-Z]+\d+\.\d+)\s*:", a.get("name", ""))
        if not m or m.group(1) not in valid:
            continue            # progress tests: totals only, no chapter split
        pts = a.get("points") or 0
        rows = sorted(a.get("attempts", []), key=lambda t: t["date"])
        out[m.group(1)] = [
            [m.group(1), t["date"], pts, round(max(0.0, pts - t["score"]), 3), 1 if i else 0]
            for i, t in enumerate(rows) if t.get("score") is not None and pts
        ]
    return out


def build_events(cache_file: Path, tests_dir: Path, valid: set,
                 grades_file: Optional[Path] = None) -> List[list]:
    cache = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    canvas = load_canvas_grades(grades_file or Path(cache_file).with_name("colp_grades.json"), valid)

    # Canvas mixed papers (Progress Tasters / Tests): wrong answers come from
    # the Canvas loader, keyed by paper and the chapter in the feedback.
    canvas_wrong = {}
    try:
        from extract_mistakes import load_canvas_wrong_answers
        for w in load_canvas_wrong_answers(Path(tests_dir)):
            key = ((w.get("source") or "").strip(), w.get("chapter"))
            canvas_wrong[key] = canvas_wrong.get(key, 0) + 1
    except Exception as e:                       # stats are best-effort
        print(f"  ⚠ Canvas wrong answers unavailable: {e}")

    attempts = {}   # dedup key -> [code, date, n, wrong]
    for fname, entry in cache.items():
        qs = entry.get("questions") or []
        if not qs:
            continue
        date = datetime.date.fromtimestamp(entry.get("mtime", 0)).isoformat()
        src = (qs[0].get("source") or "").strip()
        mixed = sum(1 for q in qs if q.get("chapter")) > len(qs) / 2

        if mixed:
            per = {}
            for q in qs:
                code = code_from_chapter(q.get("chapter"), valid)
                if code:
                    per.setdefault(code, [0, q.get("chapter")])
                    per[code][0] += 1
            for code, (n, ch) in per.items():
                w = canvas_wrong.get((src, ch), 0)
                attempts[(fname, code)] = [code, date, n, min(w, n), 0]
            continue

        code = code_from_filename(fname, valid)
        if not code or code in canvas:      # Canvas has every attempt already
            continue
        wrong = [q for q in qs if q.get("user_wrong_index") is not None]
        # The same attempt is often saved twice under two filenames. Same
        # questions AND same wrong answers = one attempt; keep the later date.
        key = (code,
               frozenset(_stem(q.get("question_text")) for q in qs),
               frozenset((_stem(q.get("question_text")), q.get("user_wrong_index")) for q in wrong))
        row = [code, date, len(qs), len(wrong), 0]
        if key not in attempts or attempts[key][1] < date:
            attempts[key] = row

    # PDF-only chapters: a second distinct attempt at the same test is a retake.
    seen = set()
    rows = sorted(attempts.values(), key=lambda r: (r[1], r[0]))
    for r in rows:
        if r[0] in canvas:
            continue
        if r[0] in seen:
            r[4] = 1
        seen.add(r[0])
    for evs in canvas.values():
        rows.extend(evs)
    return sorted(rows, key=lambda r: (r[1], r[0]))


def update_colp_html(colp_html_path: Path, cache_file: Path, tests_dir: Path) -> int:
    path = Path(colp_html_path)
    html = path.read_text(encoding="utf-8")
    m = re.search(r"SEED_DATES\s*=\s*\{(.*?)\};", html, re.S)
    valid = set(re.findall(r"'([A-Z]+\d+\.\d+)'\s*:", m.group(1))) if m else set()
    events = build_events(cache_file, tests_dir, valid)
    block = ("/*TOPIC_TEST_STATS_START*/\n"
             "// Generated by update_site.py from the COLP topic tests — do not edit.\n"
             "// [chapter, attempt date, questions answered, answered wrongly, retake]\n"
             "const TOPIC_TEST_STATS = " + json.dumps(events, separators=(",", ":")) + ";\n"
             "/*TOPIC_TEST_STATS_END*/")
    new_html, n = MARK_RE.subn(lambda _: block, html, count=1)
    if not n:
        raise ValueError("TOPIC_TEST_STATS markers not found in SQE1_COLP_Revision.html")
    if new_html != html:
        path.write_text(new_html, encoding="utf-8")
    return len(events)


if __name__ == "__main__":
    import sys
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import update_site
    html = (here / "SQE1_COLP_Revision.html").read_text(encoding="utf-8")
    valid = set(re.findall(r"'([A-Z]+\d+\.\d+)'\s*:", re.search(r"SEED_DATES\s*=\s*\{(.*?)\};", html, re.S).group(1)))
    ev = build_events(here / "_parse_cache.json", update_site.TESTS_DIR, valid)
    agg = {}
    for c, d, n, w, _ in ev:
        a = agg.setdefault(c, [0, 0, 0]); a[0] += n; a[1] += w; a[2] += 1
    print(len(ev), "attempts,", len(agg), "chapters,", sum(a[0] for a in agg.values()), "answers,", sum(a[1] for a in agg.values()), "wrong")
    for c, (n, w, k) in sorted(agg.items(), key=lambda kv: -kv[1][1] / kv[1][0])[:15]:
        print(f"  {c:10} {w:2}/{n:3} wrong  ({k} attempt{'s' if k > 1 else ''})")
