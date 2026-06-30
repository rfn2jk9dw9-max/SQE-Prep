#!/usr/bin/env python3
"""
SQE1 Personal Mistakes Extractor
──────────────────────────────────
Pulls wrong answers from:
  1. Local progress.json (mock exam sessions run via local server)
  2. Hostinger API (mock exam sessions run via GitHub Pages)
  3. Canvas PDFs in the Tests folder (SLK Taster tests)
  4. H5P PDFs in the Tests folder (BUS, CONT, LAND, etc. — user's wrong
     selections marked with WRONG_CHAR U+E894)

Maps each wrong answer to a revision guide chapter and returns
a dict of {chapter_id: [note_strings]} for injection into the HTML.
"""

import json, re, sys, urllib.request
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR   = Path('/Users/ghitab/Documents/Claude/Projects/Mission solicitor')
PROGRESS_API = 'https://bidouillecode.dev/solicitor/progress.php'

# ── Subject key normalisation ─────────────────────────────────────────────────

SUBJECT_NAME_TO_KEY = {
    "dispute resolution":               "DISP",
    "contract law":                     "CONT",
    "tort":                             "TORT",
    "business law and practice":        "BUS",
    "legal services":                   "SERV",
    "legal system":                     "LSYS",
    "property law and practice":        "PROP",
    "wills and administration":         "WILL",
    "wills and administration of estates": "WILL",
    "land law":                         "LAND",
    "criminal law and practice":        "CRMP",
    "trusts law":                       "TRUS",
    "solicitors accounts":              "SLAC",
    "criminal liability":               "CRML",
    "ethics and professional conduct":  "COND",
    "ethics":                           "COND",
    "professional conduct":             "COND",
}

def subject_to_key(subject_name: str) -> str:
    return SUBJECT_NAME_TO_KEY.get(subject_name.lower().strip(), "")


# ── Source → chapter ID mapping ───────────────────────────────────────────────

def source_to_chapter_id(source: str) -> str | None:
    """
    Extract chapter ID from source strings like:
      'DISP8.4: Commencing court proceedings: Ghita Bennis'
      'CONT1.3: Vitiating factors: Ghita Bennis'
      'SLK DISP8 manual 2025_12_15'   ← Canvas PDF source (subject-level only)
    Returns '8.4', '1.3', etc., or None if not parseable.
    """
    # Pattern 1: SUBJECT + chapter digits  e.g. DISP8.4, CONT1.3
    m = re.match(r'[A-Z]{2,6}(\d+\.\d+)', source.strip(), re.I)
    if m:
        return m.group(1)
    # Pattern 2: SLK DISP8 → subject level only, no specific chapter
    return None


# ── Progress.json reader ──────────────────────────────────────────────────────

def load_local_wrong_answers(progress_file: Path) -> list[dict]:
    if not progress_file.exists():
        return []
    try:
        sessions = json.loads(progress_file.read_text())
    except Exception:
        return []
    wrong = []
    for session in sessions:
        dt = session.get('datetime', '')
        for q in session.get('questions', []):
            if not q.get('isCorrect'):
                wrong.append({
                    'questionText': q.get('questionText', ''),
                    'subject':      q.get('subject', ''),
                    'source':       q.get('source', ''),
                    'userAnswer':   q.get('userAnswer', ''),
                    'correctAnswer':q.get('correctAnswer', ''),
                    'datetime':     dt,
                    'origin':       'mock_exam',
                })
    return wrong


# ── Hostinger API reader ──────────────────────────────────────────────────────

def load_api_wrong_answers(api_url: str) -> list[dict]:
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'SQE1-Updater/1.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        sessions = json.loads(resp.read())
    except Exception as e:
        print(f"  ⚠ Could not reach progress API: {e}")
        return []
    wrong = []
    for session in sessions:
        dt = session.get('datetime', '')
        for q in session.get('questions', []):
            if not q.get('isCorrect'):
                wrong.append({
                    'questionText': q.get('questionText', ''),
                    'subject':      q.get('subject', ''),
                    'source':       q.get('source', ''),
                    'userAnswer':   q.get('userAnswer', ''),
                    'correctAnswer':q.get('correctAnswer', ''),
                    'datetime':     dt,
                    'origin':       'mock_exam_online',
                })
    return wrong


# ── Canvas PDF wrong-answer reader ───────────────────────────────────────────

def load_canvas_wrong_answers(tests_dir: Path) -> list[dict]:
    """
    Re-parse Canvas PDFs (SLK Taster) and return questions where score = 0/1.
    Requires parse_questions.py to be importable from the same directory.
    """
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import pdfplumber, re as _re
        from parse_questions import SUBJECT_MAP, subject_from_filename, _FOOTER_RE, clean_text, scrub_option, _cell_has_colored_bg, _visible_cells
    except ImportError as e:
        print(f"  ⚠ Could not import parser: {e}")
        return []

    wrong = []
    for pdf_path in sorted(tests_dir.glob("*.pdf")):
        if not pdf_path.stem.upper().startswith("SLK"):
            continue
        subject, paper = subject_from_filename(pdf_path.name)
        source = pdf_path.stem

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                all_text = "\n".join(
                    (page.extract_text(layout=True) or "")
                    for page in pdf.pages
                )
        except Exception as e:
            print(f"  ⚠ Could not open {pdf_path.name}: {e}")
            continue

        Q_PAT = _re.compile(
            r'^\s{3,6}(\d+)\s+([\d.]+)\s*/\s*1\s+point\s+Multiple\s+Choice',
            _re.M
        )
        matches = list(Q_PAT.finditer(all_text))

        for i, m in enumerate(matches):
            score = float(m.group(2))
            if score >= 1.0:
                continue  # correct — skip

            start = m.start()
            end   = matches[i + 1].start() if i + 1 < len(matches) else len(all_text)
            block = all_text[start:end]

            # Trim at Feedback
            fb = _re.search(r'\n\s{7,}Feedback\s*\n', block)
            if fb:
                block = block[:fb.start()]

            # Extract question text (body lines at indent ~6)
            lines = block.splitlines()
            body_parts = []
            options_started = False
            correct_text = ""
            selected_text = ""

            for line in lines:
                s = line.strip()
                if not s:
                    continue
                if _re.match(r'https?://', s) or _re.match(r'Page \d+ of', s, _re.I):
                    continue
                ind = len(line) - len(line.lstrip())
                if _re.match(r'\d+\s+[\d.]+\s*/\s*1\s+point', s):
                    continue
                if _re.match(r'Correct\s+An', s, _re.I):
                    # Grab everything after "Correct An-swer:"
                    after = _re.sub(r'^Correct\s+An-?\s*(swer\s*:)?\s*', '', s, flags=_re.I)
                    correct_text += " " + after
                    continue
                if _re.match(r'swer\s*:', s, _re.I):
                    after = _re.sub(r'^swer\s*:\s*', '', s, flags=_re.I)
                    correct_text += " " + after
                    continue
                if ind >= 14 and not options_started:
                    selected_text += " " + s
                    continue
                if ind >= 9:
                    options_started = True
                    if ind >= 14:
                        selected_text += " " + s
                    continue
                if not options_started:
                    body_parts.append(s)

            question_text = clean_text(" ".join(body_parts))
            correct_text  = clean_text(correct_text)
            selected_text = clean_text(selected_text)

            if not question_text:
                continue

            wrong.append({
                'questionText':  question_text,
                'subject':       subject,
                'source':        source,
                'userAnswer':    selected_text or '(not recorded)',
                'correctAnswer': correct_text or '(see PDF)',
                'datetime':      pdf_path.stem,
                'origin':        'canvas_pdf',
            })

    return wrong


# ── Chapter mapping ───────────────────────────────────────────────────────────

def map_wrong_answers_to_chapters(wrong_answers: list[dict]) -> dict[str, list[str]]:
    """
    Returns {chapter_id: [note_string, ...]}
    chapter_id is like '8.4', '1.3' etc. (matches D object keys in the HTML)
    """
    by_chapter = defaultdict(list)

    # Deduplicate: same question text appearing multiple times
    seen = set()

    for q in wrong_answers:
        chapter_id = source_to_chapter_id(q['source'])
        if not chapter_id:
            continue  # can't map to specific chapter

        key = (chapter_id, q['questionText'][:80])
        if key in seen:
            continue
        seen.add(key)

        q_short   = q['questionText'][:200].rstrip() + ('…' if len(q['questionText']) > 200 else '')
        user_ans  = q['userAnswer'][:120].rstrip()   + ('…' if len(q['userAnswer']) > 120 else '')
        corr_ans  = q['correctAnswer'][:120].rstrip()+ ('…' if len(q['correctAnswer']) > 120 else '')

        note = f"Q: {q_short} — You answered: {user_ans}. Correct: {corr_ans}."
        by_chapter[chapter_id].append(note)

    return dict(by_chapter)


# ── HTML injection ────────────────────────────────────────────────────────────

TRAP_HEAD = "⚠ Your Personal Mistakes"

def inject_personal_notes(html: str, by_chapter: dict[str, list[str]]) -> str:
    """
    For each chapter_id in by_chapter, find the chapter in the HTML and either:
    - Replace an existing "Your Personal Mistakes" note, or
    - Append a new one before the closing ] of the notes array
    """
    for chapter_id, notes in by_chapter.items():
        if not notes:
            continue

        # Build the note JSON fragment
        body_items = json.dumps(notes, ensure_ascii=False)
        new_note = f'{{"head":"{TRAP_HEAD}","body":{body_items}}}'

        # Find the chapter by ID
        chapter_marker = f'"id":"{chapter_id}"'
        idx = html.find(chapter_marker)
        if idx == -1:
            continue

        # Find the next chapter boundary to limit our search scope
        next_chapter = html.find('"id":"', idx + len(chapter_marker))
        scope = html[idx: next_chapter if next_chapter != -1 else idx + 50000]

        # Remove existing personal mistakes note if present
        existing_pat = re.compile(
            r',\s*\{"head":"' + re.escape(TRAP_HEAD) + r'".*?\}(?=\s*[,\]])',
            re.DOTALL
        )
        scope_clean = existing_pat.sub('', scope)

        # Find the closing ] of the notes array in the (cleaned) scope
        notes_start = scope_clean.find('"notes":[')
        if notes_start == -1:
            continue
        # Find the matching ] for this notes array
        depth = 0
        notes_end = -1
        for i, ch in enumerate(scope_clean[notes_start:]):
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    notes_end = notes_start + i
                    break
        if notes_end == -1:
            continue

        # Insert the new note before the closing ]
        updated_scope = (
            scope_clean[:notes_end]
            + ',' + new_note
            + scope_clean[notes_end:]
        )

        html = html[:idx] + updated_scope + html[idx + len(scope):]
        print(f"  ✓ Injected {len(notes)} mistake(s) into chapter {chapter_id}")

    return html


# ── H5P PDF wrong-answer extraction ──────────────────────────────────────────

def load_h5p_wrong_answers(tests_dir: Path) -> list[dict]:
    """
    Parse ALL H5P PDFs (BUS, CONT, LAND, etc.) in tests_dir — including
    duplicate re-sits — and return wrong answers where the user's selection
    (WRONG_CHAR U+E894) differs from the correct answer (CORRECT_CHAR U+E90C).

    No deduplication is applied here: if the user sat the same test twice and
    got a question wrong both times, two entries are returned (they'll be
    deduped later by map_wrong_answers_to_chapters via the seen-set).
    """
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from parse_questions import parse_pdf, subject_from_filename
    except ImportError as e:
        print(f"  ⚠ Could not import parser: {e}")
        return []

    wrong = []
    pdf_paths = sorted(Path(tests_dir).glob("*.pdf"))

    for pdf_path in pdf_paths:
        if pdf_path.stem.upper().startswith("SLK"):
            continue   # SLK Canvas PDFs handled separately

        subject, paper = subject_from_filename(pdf_path.name)
        source = pdf_path.stem

        try:
            questions = parse_pdf(str(pdf_path), subject, paper)
        except Exception as e:
            print(f"  ⚠ Could not parse {pdf_path.name}: {e}")
            continue

        for q in questions:
            uidx = q.get("user_wrong_index")
            cidx = q.get("correct_index")
            if uidx is None or cidx is None or uidx == cidx:
                continue   # correct or no user answer detected

            opts = q.get("options", [])
            user_ans    = opts[uidx] if uidx < len(opts) else "?"
            correct_ans = opts[cidx] if cidx < len(opts) else "?"

            wrong.append({
                "source":        source,
                "questionText":  q["question_text"],
                "userAnswer":    user_ans,
                "correctAnswer": correct_ans,
            })

    return wrong


# ── Public entry point ────────────────────────────────────────────────────────

def get_personal_notes(tests_dir: Path, progress_file: Path) -> dict[str, list[str]]:
    print("\n[Mistakes] Loading wrong answers...")

    wrong = []

    # 1. Local mock exam sessions
    local = load_local_wrong_answers(progress_file)
    print(f"  Local progress.json: {len(local)} wrong answers")
    wrong.extend(local)

    # 2. Online mock exam sessions (GitHub Pages → Hostinger API)
    online = load_api_wrong_answers(PROGRESS_API)
    print(f"  Hostinger API: {len(online)} wrong answers")
    wrong.extend(online)

    # 3. Canvas PDFs (SLK Taster tests)
    canvas = load_canvas_wrong_answers(tests_dir)
    print(f"  Canvas PDFs: {len(canvas)} wrong answers")
    wrong.extend(canvas)

    # 4. H5P PDFs (BUS, CONT, LAND, etc. — user's wrong selections in PDF)
    h5p = load_h5p_wrong_answers(tests_dir)
    print(f"  H5P PDFs: {len(h5p)} wrong answers")
    wrong.extend(h5p)

    print(f"  Total wrong answers: {len(wrong)}")

    by_chapter = map_wrong_answers_to_chapters(wrong)
    print(f"  Mapped to {len(by_chapter)} chapter(s): {sorted(by_chapter.keys())}")
    return by_chapter


if __name__ == "__main__":
    tests_dir     = Path(SCRIPT_DIR) / "../Formation Solicitor/Tests"
    progress_file = SCRIPT_DIR / "progress.json"
    result = get_personal_notes(tests_dir, progress_file)
    for ch, notes in sorted(result.items()):
        print(f"\nChapter {ch} ({len(notes)} mistakes):")
        for n in notes:
            print(f"  • {n[:120]}")
