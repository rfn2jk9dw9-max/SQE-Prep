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


# ── Flashcard injection (mistakes → FLASH_DATA, NOT chapter notes) ───────────
#
# The revision guide has a separate flip-card flashcard feature (FLASH_DATA,
# grouped by subject) distinct from the chapter-notes prose (D-style chapter
# objects with "notes":[...], targeted by inject_personal_notes above).
# Personal mistakes belong here, in flashcards — not woven into the notes.

# Map from SUBJECT_NAME_TO_KEY's abbreviation to the actual key used in
# FLASH_DATA (most match directly; a couple differ historically).
FLASHCARD_KEY_OVERRIDES = {"BUS": "BUS7", "LSYS": "SYS"}

FLASHCARD_LABELS = {
    "DISP": "Dispute Resolution", "CONT": "Contract", "TORT": "Tort",
    "BUS7": "Business Law & Tax", "SERV": "Legal Services", "SYS": "Legal System",
    "PROP": "Property Law and Practice", "WILL": "Wills and Administration",
    "LAND": "Land Law", "CRMP": "Criminal Practice", "TRUS": "Trusts",
    "SLAC": "Solicitors Accounts", "CRML": "Criminal Law", "COND": "Conduct & Ethics",
}
FLASHCARD_COLORS = {"PROP": "#0f766e", "WILL": "#7c3aed", "SLAC": "#334155"}
DEFAULT_FLASHCARD_COLOR = "#475569"

_ORIGIN_LABEL = {
    "mock_exam": "Mock Exam", "mock_exam_online": "Mock Exam",
    "canvas_pdf": "Session", "h5p": "Session",
}

AUTO_MISTAKES_START = "/*AUTO_MISTAKES_START*/"
AUTO_MISTAKES_END = "/*AUTO_MISTAKES_END*/"


def wrong_answer_to_flashcard_key(q: dict) -> str | None:
    subj_key = subject_to_key(q.get("subject", ""))
    if not subj_key:
        return None
    return FLASHCARD_KEY_OVERRIDES.get(subj_key, subj_key)


def map_wrong_answers_to_flashcards(wrong_answers: list[dict]) -> dict[str, list[dict]]:
    """
    Returns {flashcard_key: [{"q":..., "a":..., "auto": True}, ...]}
    flashcard_key matches a FLASH_DATA deck's `key` (e.g. 'CONT', 'BUS7').
    """
    by_key = defaultdict(list)
    seen = set()

    for q in wrong_answers:
        fkey = wrong_answer_to_flashcard_key(q)
        if not fkey:
            continue

        qtext = (q.get("questionText") or "").strip()
        if not qtext:
            continue

        dedup_key = (fkey, qtext[:80])
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        label = _ORIGIN_LABEL.get(q.get("origin", "h5p"), "Session")
        q_short = qtext[:220].rstrip() + ("…" if len(qtext) > 220 else "")
        user_ans = (q.get("userAnswer") or "?")[:150].rstrip()
        corr_ans = (q.get("correctAnswer") or "?")[:150].rstrip()

        by_key[fkey].append({
            "q": f"⚠ Your mistake — {label}: {q_short}",
            "a": f"You answered: {user_ans}. Correct answer: {corr_ans}.",
            "auto": True,
        })

    return dict(by_key)


def _find_matching_bracket(text: str, open_idx: int, open_ch="[", close_ch="]") -> int:
    """
    Depth-count from open_idx (which must point at open_ch) to find the index
    of the matching close_ch, skipping over quoted string literals so that
    literal brackets inside legal text (e.g. case citations like '[2003]')
    don't throw off the count.
    """
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ("'", '"'):
            quote = ch
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def inject_mistake_flashcards(html: str, by_key: dict[str, list[dict]]) -> str:
    """
    Appends auto-generated mistake cards (tagged "auto": true) into the
    matching FLASH_DATA deck's cards:[...] array, wrapped in
    AUTO_MISTAKES_START/END comment markers so reruns replace (not
    duplicate) the batch. Creates a new deck if the subject has no deck yet.
    Hand-authored cards (no "auto" marker) are never touched.
    """
    fd_idx = html.find("const FLASH_DATA")
    if fd_idx == -1:
        print("  ⚠ FLASH_DATA not found — cannot inject mistake flashcards")
        return html

    arr_open = html.find("[", fd_idx)
    if arr_open == -1:
        return html
    arr_close = _find_matching_bracket(html, arr_open)
    if arr_close == -1:
        print("  ⚠ Could not find end of FLASH_DATA array — skipping flashcard injection")
        return html

    block = html[arr_open:arr_close + 1]

    for key, cards in by_key.items():
        if not cards:
            continue

        auto_js = ",".join(json.dumps(c, ensure_ascii=False) for c in cards)

        k_idx = block.find(f"key:'{key}'")
        if k_idx == -1:
            k_idx = block.find(f'"key":"{key}"')

        if k_idx == -1:
            # No existing deck for this subject — append a brand-new one.
            label = FLASHCARD_LABELS.get(key, key)
            color = FLASHCARD_COLORS.get(key, DEFAULT_FLASHCARD_COLOR)
            new_deck = (
                f'{{"key":"{key}","label":{json.dumps(label)},"color":"{color}","score":0,'
                f'"cards":[{AUTO_MISTAKES_START}{auto_js}{AUTO_MISTAKES_END}]}}'
            )
            trimmed = block[:-1].rstrip()
            sep = "" if trimmed.endswith(",") or trimmed.endswith("[") else ","
            block = trimmed + sep + new_deck + "]"
            print(f"  ✓ Created new flashcard deck '{key}' with {len(cards)} mistake card(s)")
            continue

        cards_marker = block.find("cards:[", k_idx)
        if cards_marker == -1:
            cards_marker = block.find('"cards":[', k_idx)
        cards_open = block.find("[", cards_marker) if cards_marker != -1 else -1
        if cards_open == -1:
            continue
        cards_close = _find_matching_bracket(block, cards_open)
        if cards_close == -1:
            continue

        scope = block[cards_open:cards_close + 1]

        auto_pat = re.compile(
            r",?\s*" + re.escape(AUTO_MISTAKES_START) + r".*?" + re.escape(AUTO_MISTAKES_END),
            re.DOTALL
        )
        scope_clean = auto_pat.sub("", scope)

        insertion = f",{AUTO_MISTAKES_START}{auto_js}{AUTO_MISTAKES_END}"
        updated_scope = scope_clean[:-1] + insertion + "]"

        block = block[:cards_open] + updated_scope + block[cards_close + 1:]
        print(f"  ✓ Injected {len(cards)} mistake flashcard(s) into '{key}' deck")

    return html[:arr_open] + block + html[arr_close + 1:]


# ── H5P PDF wrong-answer extraction ──────────────────────────────────────────

def load_h5p_wrong_answers(tests_dir: Path, cache_file: Path = None) -> list[dict]:
    """
    Parse ALL H5P PDFs (BUS, CONT, LAND, etc.) in tests_dir — including
    duplicate re-sits — and return wrong answers where the user's selection
    (WRONG_CHAR U+E894) differs from the correct answer (CORRECT_CHAR U+E90C).

    No deduplication is applied here: if the user sat the same test twice and
    got a question wrong both times, two entries are returned (they'll be
    deduped later by map_wrong_answers_to_chapters via the seen-set).

    If cache_file is given, reuses the same incremental cache format written
    by parse_questions.parse_all() ({pdf_path_str: {"mtime":..., "questions":...}})
    so PDFs already parsed in step 1 of update_site.py aren't re-parsed here.
    """
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from parse_questions import parse_pdf, subject_from_filename
    except ImportError as e:
        print(f"  ⚠ Could not import parser: {e}")
        return []

    cache = {}
    if cache_file is not None:
        cache_file = Path(cache_file)
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                cache = {}

    wrong = []
    pdf_paths = sorted(Path(tests_dir).glob("*.pdf"))
    cache_dirty = False

    for pdf_path in pdf_paths:
        if pdf_path.stem.upper().startswith("SLK"):
            continue   # SLK Canvas PDFs handled separately

        subject, paper = subject_from_filename(pdf_path.name)
        source = pdf_path.stem

        cache_key = str(pdf_path)
        mtime = pdf_path.stat().st_mtime
        cached = cache.get(cache_key)

        if cached and abs(cached.get("mtime", 0) - mtime) < 1.0:
            questions = cached["questions"]
        else:
            try:
                questions = parse_pdf(str(pdf_path), subject, paper)
            except Exception as e:
                print(f"  ⚠ Could not parse {pdf_path.name}: {e}")
                continue
            if cache_file is not None:
                cache[cache_key] = {"mtime": mtime, "questions": questions}
                cache_dirty = True

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
                "subject":       subject,
                "origin":        "h5p",
                "questionText":  q["question_text"],
                "userAnswer":    user_ans,
                "correctAnswer": correct_ans,
            })

    if cache_file is not None and cache_dirty:
        try:
            cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return wrong


# ── Public entry point ────────────────────────────────────────────────────────

def _gather_all_wrong_answers(tests_dir: Path, progress_file: Path, cache_file: Path = None) -> list[dict]:
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
    h5p = load_h5p_wrong_answers(tests_dir, cache_file=cache_file)
    print(f"  H5P PDFs: {len(h5p)} wrong answers")
    wrong.extend(h5p)

    print(f"  Total wrong answers: {len(wrong)}")
    return wrong


def get_personal_notes(tests_dir: Path, progress_file: Path, cache_file: Path = None) -> dict[str, list[str]]:
    """Legacy path: maps mistakes to chapter-notes prose. No longer used by
    update_site.py's default pipeline — mistakes now go to flashcards
    (see get_personal_mistake_flashcards) instead of the high-yield notes."""
    wrong = _gather_all_wrong_answers(tests_dir, progress_file, cache_file)
    by_chapter = map_wrong_answers_to_chapters(wrong)
    print(f"  Mapped to {len(by_chapter)} chapter(s): {sorted(by_chapter.keys())}")
    return by_chapter


def get_personal_mistake_flashcards(tests_dir: Path, progress_file: Path, cache_file: Path = None) -> dict[str, list[dict]]:
    """Maps mistakes to FLASH_DATA flashcard decks, keyed by subject."""
    wrong = _gather_all_wrong_answers(tests_dir, progress_file, cache_file)
    by_key = map_wrong_answers_to_flashcards(wrong)
    total = sum(len(v) for v in by_key.values())
    print(f"  Mapped to {total} flashcard(s) across {len(by_key)} deck(s): {sorted(by_key.keys())}")
    return by_key


if __name__ == "__main__":
    tests_dir     = Path(SCRIPT_DIR) / "../Formation Solicitor/Tests"
    progress_file = SCRIPT_DIR / "progress.json"
    result = get_personal_notes(tests_dir, progress_file)
    for ch, notes in sorted(result.items()):
        print(f"\nChapter {ch} ({len(notes)} mistakes):")
        for n in notes:
            print(f"  • {n[:120]}")
