#!/usr/bin/env python3
"""SQE1 Question Bank Parser — with cross-page table stitching"""
import json, os, re, sys
import pdfplumber
from pathlib import Path
from collections import defaultdict

CORRECT_CHAR = chr(0xE90C)   # H5P correct-answer glyph (U+E90C, private-use area)
WRONG_CHAR   = chr(0xE894)   # H5P wrong-answer glyph   (U+E894)
# Strip all private-use area glyphs (U+E000–U+F8FF) from text
_PUA_RE = re.compile(r'[-]')

SUBJECT_MAP = {
    "BUS":  ("Business Law and Practice",          "FLK1", 20),
    "CONT": ("Contract Law",                        "FLK1", 18),
    "TORT": ("Tort",                                "FLK1", 16),
    "DISP": ("Dispute Resolution",                  "FLK1", 20),
    "SERV": ("Legal Services",                      "FLK1", 14),
    "LSYS": ("Legal System",                        "FLK1", 12),
    "SYS":  ("Legal System",                        "FLK1", 12),
    "PROP": ("Property Law and Practice",           "FLK2", 20),
    "WILL": ("Wills and Administration of Estates", "FLK2", 18),
    "LAND": ("Land Law",                            "FLK2", 16),
    "CRMP": ("Criminal Law and Practice",           "FLK2", 16),
    "TRUS": ("Trusts Law",                          "FLK2", 14),
    "SLAC": ("Solicitors Accounts",                 "FLK2",  8),
    "CRML": ("Criminal Liability",                  "FLK2",  8),
    "COND": ("Ethics and Professional Conduct",     "BOTH",  0),
}

def _dbg(*args, **kwargs):
    try:
        print(*args, file=sys.stderr, **kwargs)
    except (OSError, BrokenPipeError):
        pass

def subject_from_filename(name):
    stem = Path(name).stem.upper()
    for prefix, info in SUBJECT_MAP.items():
        if stem.startswith(prefix):
            return info[0], info[1]
    if stem.startswith("SLK"):
        return "Mixed Practice", "BOTH"
    return "Unknown", "BOTH"

def clean_text(text):
    """Remove H5P/Canvas icon glyphs and collapse whitespace."""
    text = _PUA_RE.sub("", text)   # strip all private-use area glyphs
    lines = [l.strip() for l in text.splitlines()]
    return " ".join(l for l in lines if l)

# ── H5P footer / metadata scrub pattern ─────────────────────────────────────
# Strips URL footers, page numbers, and score lines from option cell text.
_FOOTER_RE = re.compile(
    r'https?://\S+'                       # full https/http URL
    r'|(?<!\w)tps?://\S+'                 # truncated http(s):// fragment
    r'|collaw\S*'                          # ColLaw domain fragment
    r'|h5p\.com\S*'                        # H5P domain fragment
    r'|lti/launch\S*'                      # LTI launch path
    r'|Page\s+\d+\s+of(?:\s+\d+)?'        # "Page N of M" or "Page N of"
    r'|Question\s+Score\s*:[\s\d./]+'     # "Question Score: 0 / 1"
    r'|Total\s+Score\s*[:\s][\s\d./%()]+'   # "Total Score: 0/1" or "Total Score 6/10 (60%)"
    r'|Start\s+Time[^\n]*'
    r'|End\s+Time[^\n]*'
    r'|Spent\s+(Time?|\d)[^\n]*'            # "Spent Time: ..." or "Spent 2 hours ..." 
    r'|H5P\.com[^\n]*'
    r'|5P\.com[^\n]*',
    re.I,
)

def scrub_option(raw_text):
    """Strip footer/metadata from option cell text; return cleaned text."""
    if not raw_text:
        return ""
    text = _FOOTER_RE.sub("", raw_text)
    text = _PUA_RE.sub("", text)   # strip all private-use area glyphs
    return " ".join(text.split())


def _cell_has_colored_bg(page, cell_bbox):
    """Return True if the cell has a non-white, non-black fill (H5P correct-answer highlight)."""
    x0, top, x1, bottom = cell_bbox
    try:
        for rect in page.rects:
            rx0  = rect.get("x0",  0)
            rtop = rect.get("top", 0)
            rx1  = rect.get("x1",  0)
            rbot = rect.get("bottom", 0)
            if not (rx0 < x1 and rx1 > x0 and rtop < bottom and rbot > top):
                continue
            if not rect.get("fill"):
                continue
            color = rect.get("non_stroking_color")
            if color is None:
                continue
            if isinstance(color, (int, float)):
                color = (color,)
            if all(c > 0.85 for c in color):
                continue   # white
            if all(c < 0.15 for c in color):
                continue   # black
            return True
    except Exception:
        pass
    return False


# ── Page-level helpers ───────────────────────────────────────────────────────

def _bands_in_region(page, y0, y1, x0, x1):
    """
    Build option-row bands from H5P row-separator rects.

    H5P draws a thin (≈0.8pt) light-grey filled rect between answer rows.
    pdfplumber's table finder is unreliable here: the ✓/✗ icon's vector
    graphics create spurious cell boundaries that (a) split the correct-answer
    row so the glyph lands in the *previous* option's cell, and (b) merge two
    adjacent options into one cell.  Deriving rows directly from the separator
    rects avoids both failure modes.

    Returns a list of (x0, top, x1, bottom) bands between y0 and y1, or []
    if no separators are found (caller should fall back to table cells).
    """
    min_w = 0.5 * (x1 - x0)
    seps = []
    for r in page.rects:
        try:
            if not r.get("fill"):
                continue
            if (r["bottom"] - r["top"]) > 3:
                continue
            if (r["x1"] - r["x0"]) < min_w:
                continue
            if r["top"] < y0 - 2 or r["bottom"] > y1 + 2:
                continue
            seps.append((r["top"], r["bottom"]))
        except Exception:
            pass
    if not seps:
        return []
    # Merge separator segments drawn per-column (same y, different x ranges)
    seps.sort()
    merged = []
    for top, bot in seps:
        if merged and abs(top - merged[-1][0]) < 1.5:
            merged[-1][1] = max(merged[-1][1], bot)
        else:
            merged.append([top, bot])
    # Bands between consecutive boundaries.  The region start y0 opens the
    # first band (the separator under the header may sit slightly ABOVE
    # header_bottom, in which case the sliver band is skipped); each
    # separator closes one band and opens the next; y1 closes the last.
    starts = [y0] + [b for _, b in merged]
    ends   = [t for t, _ in merged] + [y1]
    bands = []
    for band_top, band_bot in zip(starts, ends):
        if band_bot - band_top >= 6:   # skip degenerate slivers
            bands.append((x0, band_top, x1, band_bot))
    return bands


def _char_row_index(page, opt_cells, char, col_x0=None, col_x1=None):
    """
    Find the option row containing a marker glyph by scanning page.chars
    directly and assigning by the glyph's vertical CENTER (crop-intersection
    can leak a glyph into an adjacent row).  Optional x-range restricts the
    search to one column (e.g. the "Correct" column).
    """
    try:
        for c in page.chars:
            if c["text"] != char:
                continue
            cx = (c["x0"] + c["x1"]) / 2
            if col_x0 is not None and cx < col_x0 - 2:
                continue
            if col_x1 is not None and cx > col_x1 + 2:
                continue
            cy = (c["top"] + c["bottom"]) / 2
            for idx, cb in enumerate(opt_cells):
                if cb[1] <= cy <= cb[3]:
                    return idx
    except Exception:
        pass
    return None


def _visible_cells(page):
    """All table cells whose bounding box lies within (or very near) the page.

    Outer container cells — cells from the multi-page spanning TABLE 0 that
    merely wrap the real option rows — are excluded.  A cell is considered a
    container if another visible cell fits strictly inside its bounding box
    (with 2 pt tolerance).  Removing containers prevents their concatenated
    option text from polluting continuation slots.
    """
    ph, pw = page.height, page.width
    seen = set()
    raw = []
    for tbl in page.find_tables():
        for cb in tbl.cells:
            if cb in seen:
                continue
            seen.add(cb)
            x0, top, x1, bot = cb
            if x0 < 0 or top < -5 or bot > ph + 10 or x1 > pw + 10:
                continue
            raw.append(cb)

    # Drop any cell that contains another visible cell (outer-container dedup).
    def _contains(outer, inner):
        return (inner[0] >= outer[0] - 2 and inner[1] >= outer[1] - 2
                and inner[2] <= outer[2] + 2 and inner[3] <= outer[3] + 2
                and (inner[0] > outer[0] + 1 or inner[1] > outer[1] + 1
                     or inner[2] < outer[2] - 1 or inner[3] < outer[3] - 1))

    containers = {cb for cb in raw
                  if any(_contains(cb, oc) for oc in raw if oc is not cb)}
    result = [cb for cb in raw if cb not in containers]

    return sorted(result, key=lambda c: (round(c[1], 1), round(c[0], 1)))


def _first_answers_y(page, cells):
    """Return the top-y of the first 'Answers' header cell on this page, or inf."""
    for cb in cells:
        try:
            if (page.crop(cb).extract_text() or "").strip() == "Answers":
                return cb[1]
        except Exception:
            pass
    return float("inf")


def _extract_option_cells(page, tbl_cells, header_bottom, pw, ph):
    """
    Return up to 5 option cells (below the Answers header, in the left portion
    of the page).  Tries progressively wider x-thresholds.
    Only returns cells fully within the page.
    Returns whatever is found (even 1-3 cells) so partial options are captured
    and the continuation mechanism can fill the rest from the next page.
    """
    for x_frac in (0.42, 0.58, 0.72, 1.0):
        opts = [c for c in tbl_cells
                if c[1] >= header_bottom - 2
                and c[0] < pw * x_frac
                and c[1] >= 0 and c[3] <= ph + 5][:5]
        if len(opts) >= 4:   # prefer 4+ (complete or near-complete question)
            return opts
    # Accept any partial options found rather than returning nothing
    for x_frac in (0.42, 0.58, 0.72, 1.0):
        opts = [c for c in tbl_cells
                if c[1] >= header_bottom - 2
                and c[0] < pw * x_frac
                and c[1] >= 0 and c[3] <= ph + 5][:5]
        if opts:
            return opts
    return []


def _extract_orphan_qtxts(page):
    """
    Find question texts from tables whose Answers header lies BEYOND the bottom
    of the current page (the table continues onto the next page).
    These question texts need to be passed to the next page's parser.
    Returns a list of clean question-text strings (usually 0 or 1 items).
    """
    ph = page.height
    orphans = []
    for tbl in page.find_tables():
        cells = sorted(tbl.cells, key=lambda c: (round(c[1], 1), round(c[0], 1)))

        # Skip tables that already have their Answers header on this page
        has_answers = False
        for cb in cells:
            if cb[1] < 0 or cb[3] > ph + 10:
                continue
            try:
                if (page.crop(cb).extract_text() or "").strip() == "Answers":
                    has_answers = True
                    break
            except Exception:
                pass
        if has_answers:
            continue

        # Only consider tables that overflow (or nearly reach) the page bottom
        # — question text stranded at the foot of a page has its Answers
        # section on the next page even when the table doesn't overflow.
        overflows = any(cb[3] > ph for cb in cells)
        if not overflows and not any(cb[3] > ph - 40 for cb in cells):
            continue

        # Find question text cell visible on this page
        for cb in cells:
            if cb[1] < 0 or cb[3] > ph + 5:
                continue
            try:
                raw = page.crop(cb).extract_text() or ""
                # For non-overflowing (near-bottom) tables, only a text block
                # explicitly starting "Question N" is a safe orphan candidate —
                # anything else is leftover option text from an earlier question.
                if not overflows and not re.match(r"\s*Question \d+", raw):
                    continue
                raw = re.sub(r"^\s*Question \d+\s*\n?", "", raw).strip()
                raw = re.sub(r"\s*Question Score:\s*[\d.]+\s*/\s*\d+\s*$", "", raw).strip()
                raw = _FOOTER_RE.sub(" ", raw).strip()
                txt = clean_text(raw)
                if (txt and txt != "Answers"
                        and "User's Answer" not in txt
                        and not txt.startswith("Correct")
                        and not re.search(
                            r'Spent\s+\d|Total\s+Score|Out\s+of\s+\d+'
                            r'|Time\s+for\s+this|Attempt\s+\d',
                            txt, re.I)):
                    orphans.append(txt)
                    break
            except Exception:
                pass
    return orphans


# ── Core page parser ─────────────────────────────────────────────────────────

def _extract_page_stubs(page, orphan_qtxts=None):
    """
    Parse all question stubs on one page.
    Returns list of dicts:
      { qtxt, opts:[str×5], cidx:int|None, complete:bool }
    'opts' may have empty strings for options that continue on the next page.

    orphan_qtxts: list of question texts from the previous page whose Answers
    section starts at the top of this page (cross-page question text).
    The list is consumed (popped) as orphans are used.
    """
    ph, pw = page.height, page.width
    stubs = []
    if orphan_qtxts is None:
        orphan_qtxts = []

    for tbl in page.find_tables():
        cells = sorted(tbl.cells, key=lambda c: (round(c[1], 1), round(c[0], 1)))

        # ── Find Answers header and Correct column x-boundary ───────────────
        header_bottom  = None
        correct_col_x0 = None   # x-start of the "Correct" column header cell
        correct_col_x1 = None   # x-end   of the "Correct" column header cell
        for cb in cells:
            if cb[1] < 0 or cb[3] > ph + 10:
                continue
            try:
                txt = (page.crop(cb).extract_text() or "").strip()
                if txt == "Answers" and header_bottom is None:
                    header_bottom = cb[3]
                elif txt.lower().startswith("correct") and correct_col_x0 is None:
                    correct_col_x0 = cb[0]
                    correct_col_x1 = cb[2]
            except Exception:
                pass
            if header_bottom is not None and correct_col_x0 is not None:
                break
        if header_bottom is None:
            continue
        # Fallback Correct-column bounds: rightmost ~18% of page
        if correct_col_x0 is None:
            correct_col_x0 = pw * 0.82
            correct_col_x1 = pw

        # ── Find question text cell (first visible cell before Answers) ──────
        q_cell = None
        for cb in cells:
            if cb[1] < 0 or cb[3] > ph + 10:
                continue
            if cb[3] > header_bottom + 2:
                continue
            try:
                txt = (page.crop(cb).extract_text() or "").strip()
                if (txt and txt != "Answers"
                        and "User's Answer" not in txt
                        and not txt.startswith("Correct")):
                    q_cell = cb
                    break
            except Exception:
                pass
        if q_cell is None:
            # No valid q_cell on this page — consume an orphan if available
            # (question whose text was on the previous page)
            if orphan_qtxts:
                question_text = orphan_qtxts.pop(0)
            else:
                continue
        else:
            # ── Extract question text ────────────────────────────────────────
            try:
                q_raw = page.crop(q_cell).extract_text() or ""
            except Exception:
                if orphan_qtxts:
                    question_text = orphan_qtxts.pop(0)
                else:
                    continue
            else:
                q_raw = re.sub(r"^Question \d+\s*\n?", "", q_raw).strip()
                q_raw = re.sub(r"\s*Question Score:\s*[\d.]+\s*/\s*\d+\s*$", "", q_raw).strip()
                q_raw = _FOOTER_RE.sub(" ", q_raw).strip()
                question_text = clean_text(q_raw)
                if not question_text:
                    # q_cell found but text stripped to nothing — try orphan
                    if orphan_qtxts:
                        question_text = orphan_qtxts.pop(0)
                    else:
                        continue

        # ── Extract option cells ─────────────────────────────────────────────
        # Prefer separator-rect row bands (robust against ✓-icon cell-split /
        # option-merge artifacts); fall back to table cells if none found.
        tb = tbl.bbox
        opt_cells = _bands_in_region(
            page, max(0, header_bottom), min(tb[3], ph), tb[0], tb[2]
        )[:5]
        if not opt_cells:
            opt_cells = _extract_option_cells(page, cells, header_bottom, pw, ph)

        options = []
        cidx    = None

        # Extract option text (no correct-detection here — see below)
        for cb in opt_cells:
            try:
                raw = page.crop(cb).extract_text() or ""
                options.append(scrub_option(raw))
            except Exception:
                options.append("")

        # ── Correct-answer detection ──────────────────────────────────────────
        # The original approach (CORRECT_CHAR in full-width row crop) was broken:
        # all 5 row crops span x=27–568 and pdfplumber returns CORRECT_CHAR in
        # every one, so cidx was always overwritten to the last option (index 4 = E).
        #
        # Fix: try four methods in order, stopping as soon as cidx is found.

        # 0) Direct char scan: CORRECT_CHAR glyph in the "Correct" column,
        #    assigned to the row containing the glyph's vertical center.
        #    (Most reliable — immune to crop-intersection leakage.)
        cidx = _char_row_index(page, opt_cells, CORRECT_CHAR,
                               col_x0=correct_col_x0, col_x1=correct_col_x1)

        # 1) Background colour: H5P marks the correct option with a coloured cell.
        if cidx is None:
            for idx, cb in enumerate(opt_cells):
                if _cell_has_colored_bg(page, cb):
                    cidx = idx
                    break

        # 2) CORRECT_CHAR in the "Correct" column only.
        #    correct_col_x0/x1 were found from the header row above; this narrow
        #    crop is row-specific so CORRECT_CHAR only appears in the right row.
        if cidx is None:
            for idx, cb in enumerate(opt_cells):
                try:
                    x0 = max(correct_col_x0, cb[0])
                    x1 = min(correct_col_x1, cb[2]) if correct_col_x1 else cb[2]
                    if x0 < x1:
                        cor_raw = page.crop((x0, cb[1], x1, cb[3])).extract_text() or ""
                        if CORRECT_CHAR in cor_raw:
                            cidx = idx
                            break
                except Exception:
                    pass

        # 3) Last resort: CORRECT_CHAR anywhere — but stop at the FIRST match
        #    (the original code lacked the break, causing cidx to always end at E).
        if cidx is None:
            for idx, cb in enumerate(opt_cells):
                try:
                    raw_chk = page.crop(cb).extract_text() or ""
                    if CORRECT_CHAR in raw_chk:
                        cidx = idx
                        break   # ← critical: stop at first match
                except Exception:
                    pass

        # ── User-answer detection (wrong-answer tracking) ──────────────────────
        # WRONG_CHAR (U+E894) appears in the user's selected option when they
        # chose incorrectly.  We scan each option cell's full-width crop for it.
        # uidx is None when the user was correct (no WRONG_CHAR present).
        uidx = _char_row_index(page, opt_cells, WRONG_CHAR)
        if uidx is None:
            for idx, cb in enumerate(opt_cells):
                try:
                    raw_chk = page.crop(cb).extract_text() or ""
                    if WRONG_CHAR in raw_chk:
                        uidx = idx
                        break
                except Exception:
                    pass

        # Whether the last row WITH TEXT may be cut mid-sentence at the page
        # bottom.  Only possible when the table itself overflows the page
        # (tb[3] > ph); if the table closes on this page, every rendered row
        # is complete and next-page text is a whole new option.  The final
        # mid-sentence test (no terminal punctuation) happens in
        # _apply_continuation.
        tail_cut = bool(tb[3] > ph + 2 and any(options))

        # Pad to 5 with empty strings (continuation expected from next page)
        while len(options) < 5:
            options.append("")

        # If the last option cell reaches near the page bottom, the cell is
        # visually truncated — the question must continue on the next page.
        last_cell_near_bottom = (
            opt_cells
            and opt_cells[-1][3] >= ph - 100
        )
        complete = (
            len(options) == 5
            and all(options)
            and cidx is not None
            and not last_cell_near_bottom
        )
        stubs.append({"qtxt": question_text, "opts": options,
                      "cidx": cidx, "uidx": uidx, "complete": complete,
                      "tail_cut": tail_cut})

    return stubs


def _apply_continuation(pending, page, cont_cells):
    """
    Try to complete a pending question using cells from the top of the next page.
    Mutates `pending` in place.  Empty slots get filled; the last option
    (if partial) gets its text appended.
    """
    seen_texts = set()   # dedup: skip cells whose text was already processed
    for cb in cont_cells:
        try:
            raw     = page.crop(cb).extract_text() or ""
            cleaned = scrub_option(raw)
            if not cleaned:
                continue
            # Skip pure page-furniture fragments (dates, "9/9", times)
            if re.match(r'^[\d\s/:,.\-]+$', cleaned):
                continue
            # Stop processing if we've hit the start of the next question
            if re.match(r'Question\s+\d+\s', cleaned, re.I):
                break
            # Skip duplicate text (outer-container cell repeating inner cell content)
            if cleaned in seen_texts:
                continue
            seen_texts.add(cleaned)
            has_cor  = CORRECT_CHAR in raw
            has_wrong = WRONG_CHAR in raw

            # Detect a split-cell continuation: the text starts with a
            # lowercase letter AND the last filled option ended without a
            # sentence-ending character (i.e. the page boundary cut mid-word
            # or mid-sentence).  In that case append to the last filled slot
            # rather than filling the next empty slot.
            last_filled_idx = next(
                (i for i in range(len(pending["opts"]) - 1, -1, -1)
                 if pending["opts"][i]),
                None,
            )
            # A cell is a split-page continuation of the previous option when
            # the previous option text doesn't end with sentence-ending punctuation
            # (it was cut at a page boundary mid-sentence).
            # We no longer require the continuation to start lowercase — proper
            # nouns like "Ombudsman" can begin a continuation fragment.
            is_split_continuation = (
                pending.get("tail_cut", True)   # last filled row was cut at page bottom
                and last_filled_idx is not None
                and cleaned
                and pending["opts"][last_filled_idx][-1:] not in {'.', '?', '!', '"', '”'}
            )

            empty = [i for i, o in enumerate(pending["opts"]) if not o]
            # The cut-row rejoin only applies to the FIRST text cell of the
            # continuation page; later cells are whole new options.
            pending["tail_cut"] = False
            if is_split_continuation:
                # Re-join the fragment that was cut at the page boundary
                pending["opts"][last_filled_idx] = (
                    pending["opts"][last_filled_idx] + " " + cleaned
                ).strip()
                if has_cor:
                    pending["cidx"] = last_filled_idx
                if has_wrong and pending.get("uidx") is None:
                    pending["uidx"] = last_filled_idx
            elif empty:
                # Fill next empty slot (options C/D/E entirely on next page)
                idx = empty[0]
                pending["opts"][idx] = cleaned
                if has_cor:
                    pending["cidx"] = idx
                if has_wrong and pending.get("uidx") is None:
                    pending["uidx"] = idx
            else:
                # Append to last option (option E was split mid-sentence)
                pending["opts"][-1] = (pending["opts"][-1] + " " + cleaned).strip()
                if has_cor:
                    pending["cidx"] = len(pending["opts"]) - 1
                if has_wrong and pending.get("uidx") is None:
                    pending["uidx"] = len(pending["opts"]) - 1
        except Exception:
            pass

    # Colour fallback for correct_idx
    if pending["cidx"] is None:
        for cb in cont_cells:
            if _cell_has_colored_bg(page, cb):
                empty = [i for i, o in enumerate(pending["opts"]) if not o]
                idx   = empty[0] if empty else len(pending["opts"]) - 1
                pending["cidx"] = idx
                break


# ── PDF entry point ───────────────────────────────────────────────────────────

def _make_q(stub, subject, paper, source):
    q = {
        "question_text": stub["qtxt"],
        "options":       stub["opts"],
        "correct_index": stub["cidx"],
        "subject":       subject,
        "paper":         paper,
        "source":        source,
    }
    if stub.get("uidx") is not None:
        q["user_wrong_index"] = stub["uidx"]
    return q


def parse_pdf(pdf_path, subject, paper):
    questions = []
    pending      = None   # question stub waiting for option continuation from next page
    orphan_qtxts = []     # question texts whose Answers section is on the next page
    source       = Path(pdf_path).stem

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                vcells     = _visible_cells(page)
                first_ay   = _first_answers_y(page, vcells)

                # ── Complete pending from previous page ──────────────────────
                if pending is not None:
                    # Prefer separator-rect row bands from the continuation
                    # table (the table hugging the page top) — same rationale
                    # as in _extract_page_stubs: table cells get corrupted by
                    # the ✓/✗ icon vector graphics.
                    cont = None
                    # Clip table bboxes to the visible page: some H5P exports
                    # use virtual-page coordinates (negative tops, bottoms
                    # beyond page height).
                    cand = []
                    for t in page.find_tables():
                        t_top = max(0, t.bbox[1])
                        t_bot = min(page.height, t.bbox[3])
                        if t_top <= 45 and (t_bot - t_top) >= 20:
                            cand.append((t_bot - t_top, t_top, t_bot, t))
                    if cand:
                        _, t_top, t_bot, t0 = min(cand, key=lambda c: c[0])
                        bands = _bands_in_region(
                            page, t_top, t_bot, t0.bbox[0], t0.bbox[2],
                        )
                        if bands:
                            cont = bands
                    if cont is None:
                        cont = [c for c in vcells if c[3] <= first_ay + 2]
                    if not cont:
                        # Last resort: no tables detected at all (e.g. a lone
                        # trailing option row on the final page) — build bands
                        # straight from the separator rects on the page.
                        y_end = first_ay if first_ay != float("inf") else page.height
                        cont = _bands_in_region(page, 0, y_end,
                                                27, page.width - 27)
                    _apply_continuation(pending, page, cont)

                    if (len(pending["opts"]) == 5
                            and all(pending["opts"])
                            and pending["cidx"] is not None):
                        questions.append(_make_q(pending, subject, paper, source))
                    else:
                        _dbg(f"  SKIP (still incomplete after cont, "
                             f"blank={[i for i,o in enumerate(pending['opts']) if not o]}, "
                             f"cidx={pending['cidx']}): {pending['qtxt'][:60]!r}")
                    pending = None

                # ── Collect orphan question texts for next page ──────────────
                # (questions whose text is on this page but Answers are on next)
                new_orphans = _extract_orphan_qtxts(page)

                # ── Parse stubs from this page ───────────────────────────────
                for stub in _extract_page_stubs(page, orphan_qtxts):
                    if stub["complete"]:
                        questions.append(_make_q(stub, subject, paper, source))
                    else:
                        if pending is not None:
                            _dbg(f"  SKIP (new stub displaced pending): "
                                 f"{pending['qtxt'][:60]!r}")
                        pending = stub

                # Pass new orphan texts to the next page's parser
                orphan_qtxts = new_orphans

    except Exception as e:
        _dbg(f"  ERROR {Path(pdf_path).name}: {e}")

    # Final pending at EOF
    if pending is not None:
        if (len(pending["opts"]) == 5
                and all(pending["opts"])
                and pending["cidx"] is not None):
            questions.append(_make_q(pending, subject, paper, source))
        else:
            _dbg(f"  SKIP (EOF, incomplete): {pending['qtxt'][:60]!r}")

    return questions


# ── Canvas LMS quiz-results PDF parser ───────────────────────────────────────

def _parse_canvas_block(block, score):
    """
    Parse one Canvas LMS quiz question block (already trimmed at 'Feedback').
    Returns {question_text, options:[5 str], correct_index:int} or None.

    Layout rules (from extract_text(layout=True)):
      • Question body lines: leading indent ≈ 6
      • Regular option lines: leading indent ≈ 10
      • Selected option lines: leading indent ≈ 16
      • "Correct An-" / "swer:" label (0/1 questions): indent ≈ 6
    For 1/1 questions the selected option IS the correct answer.
    For 0/1 questions the "Correct An-"/"swer:" text names the correct option.
    """
    lines = block.splitlines()
    classified = []
    for line in lines:
        s = line.strip()
        if re.match(r'https?://', s):                   continue
        if re.match(r'Page \d+ of', s, re.I):           continue
        if re.match(r'Quizzes\s*-\s*Results', s, re.I): continue
        if re.match(r'\d\d/\d\d/\d{4}', s):             continue
        ind = len(line) - len(line.lstrip()) if s else -1
        classified.append((ind, s))

    # Skip past the question header line ("N  X/1 point Multiple Choice")
    start_idx = 0
    for j, (ind, txt) in enumerate(classified):
        if re.match(r'\d+\s+[\d.]+\s*/\s*1\s+point', txt):
            start_idx = j + 1
            break
    classified = classified[start_idx:]

    body_parts    = []
    option_groups = []   # list of [is_selected:bool, parts:list[str]]
    correct_parts = []   # text fragments from "Correct An-"/"swer:" label
    state = 'body'

    for ind, txt in classified:
        if ind == -1:           # blank line — skip without flushing
            continue

        # ── "Correct Answer:" label (0/1 questions) ──────────────────────────
        # Taster format: "Correct An-" / "swer: [answer]"
        if ind <= 8 and re.match(r'Correct\s+An', txt, re.I):
            state = 'correct'
            after = re.sub(r'^Correct\s+An-?\s*', '', txt, flags=re.I).strip()
            if after:
                correct_parts.append(after)
            continue

        # Tests format A: "Correct   [answer text on same line]"
        if ind <= 8 and re.match(r'Correct\s+(?!An)', txt, re.I):
            after = re.sub(r'^Correct\s+', '', txt, flags=re.I).strip()
            if after:
                correct_parts.append(after)
            state = 'correct_inline'
            continue

        # Tests format B: "Correct" standalone, answer on next high-indent line
        if ind <= 8 and re.match(r'Correct\s*$', txt, re.I):
            state = 'correct'
            continue

        # "Answer:" label — marks end of correct-answer section
        if ind <= 8 and re.match(r'Answer\s*:', txt, re.I):
            state = 'options'
            continue

        if state == 'correct_inline':
            # After inline Correct, next low-indent line is "Answer:" (handled above)
            # High-indent continuation of answer text
            if ind >= 6:
                correct_parts.append(txt)
            continue

        if state == 'correct':
            if re.match(r'swer\s*:', txt, re.I):
                after = re.sub(r'^swer\s*:\s*', '', txt, flags=re.I).strip()
                if after:
                    correct_parts.append(after)
                state = 'options'
            elif ind >= 14:     # text between "Correct An-" and "swer:" (2-line form)
                correct_parts.append(txt)
            continue            # stay in 'correct' until "swer:" consumed

        # ── Body ──────────────────────────────────────────────────────────────
        if state == 'body':
            if ind >= 9:        # first option line — switch state
                state = 'options'
            else:
                body_parts.append(txt)
                continue

        # ── Options ───────────────────────────────────────────────────────────
        if state == 'options':
            is_sel = (ind >= 14)
            if is_sel:
                # Selected option (indent ~16): extend current selected group or start one
                if option_groups and option_groups[-1][0]:
                    option_groups[-1][1].append(txt)
                else:
                    option_groups.append([True, [txt]])
            else:
                # Regular option (indent ~10)
                # New option when: first option, starts uppercase/digit/symbol, or previous was selected
                starts_upper = bool(txt) and (txt[0].isupper() or txt[0].isdigit() or txt[0] in '£$€(')
                if not option_groups or starts_upper or option_groups[-1][0]:
                    option_groups.append([False, [txt]])
                else:
                    # Lowercase continuation of the previous regular option
                    option_groups[-1][1].append(txt)

    # ── Assemble result ───────────────────────────────────────────────────────
    qtxt = clean_text(" ".join(body_parts))
    opts_list = [
        (sel, clean_text(" ".join(parts)))
        for sel, parts in option_groups
        if " ".join(parts).strip()
    ]

    if not qtxt or len(opts_list) < 5:
        _dbg(f"  CANVAS-BLOCK: {len(opts_list)} opts for: {qtxt[:60]!r}")
        return None

    opts_list = opts_list[:5]
    options   = [t for _, t in opts_list]

    if score >= 1.0:
        # Correct answer = the selected option
        cidx = next((j for j, (sel, _) in enumerate(opts_list) if sel), None)
    else:
        # Correct answer = best word-overlap match against correct_parts text
        correct_text = clean_text(" ".join(correct_parts))
        cidx = None
        if correct_text:
            cw   = set(correct_text.lower().split())
            best = -1.0
            for j, (_, opt_text) in enumerate(opts_list):
                ow = set(opt_text.lower().split())
                if not ow or not cw:
                    continue
                overlap = len(ow & cw) / min(len(ow), len(cw))
                if overlap > best:
                    best = overlap
                    cidx = j
        if cidx is None:
            _dbg(f"  CANVAS-BLOCK: no correct match for: {correct_text[:60]!r}")
            return None

    return {
        "question_text": qtxt,
        "options":       options,
        "correct_index": cidx,
    }


def parse_canvas_pdf(pdf_path, subject, paper):
    """Parse a Canvas LMS quiz results PDF (SLK Taster format, 20 questions each)."""
    source    = Path(pdf_path).stem
    questions = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = "\n".join(
                (page.extract_text(layout=True) or "")
                for page in pdf.pages
            )
    except Exception as e:
        _dbg(f"  ERROR opening {Path(pdf_path).name}: {e}")
        return questions

    Q_PAT   = re.compile(
        r'^\s{3,6}(\d+)\s+([\d.]+)\s*/\s*1\s+point\s+Multiple\s+[Cc]hoice',
        re.M
    )
    matches = list(Q_PAT.finditer(all_text))
    _dbg(f"  Canvas: {len(matches)} question headers in {Path(pdf_path).name}")

    for i, m in enumerate(matches):
        q_num = int(m.group(1))
        score = float(m.group(2))
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(all_text)
        block = all_text[start:end]

        # Trim at the Feedback section
        fb = re.search(r'\n\s{7,}Feedback\s*\n', block)
        if fb:
            block = block[:fb.start()]

        result = _parse_canvas_block(block, score)
        if result:
            result.update({"subject": subject, "paper": paper, "source": source})
            questions.append(result)
        else:
            _dbg(f"  CANVAS SKIP Q{q_num} in {Path(pdf_path).name}")

    return questions


def _norm_opt(s):
    """Normalise text for override matching: lowercase, strip all non-alphanumerics.

    Absorbs the differences that otherwise defeat exact equality — curly vs
    straight apostrophes, non-breaking spaces, £/currency spacing, double
    spaces, trailing punctuation, and the parser's mid-word truncation.

    Used for BOTH the question_prefix match and the correct_text match. The
    question_prefix needs it too: the 'A defendant's trial is at the Crown
    Court' override silently matched nothing for months purely because the
    override file had a straight apostrophe and the PDF has a curly one.
    """
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


SENTENCE_END = re.compile(r'(?<=[.?!])\s+')


def _is_continuation(prev: str, frag: str) -> bool:
    """
    True when `frag` is the tail of `prev` that the parser split into its own
    option. Signature: the previous option is a long clause with no terminal
    punctuation, and the fragment opens in lower case.

    The length floor matters — options like 'LLP', 'plc', 'ltd' are short,
    unpunctuated and lower case, and are NOT continuations of each other.
    """
    prev, frag = (prev or '').strip(), (frag or '').strip()
    if not prev or not frag:
        return False
    if len(prev) < 40:
        return False
    if re.search(r'[.?!]$', prev):
        return False
    return frag[0].islower()


def _split_merged_option(text: str, siblings: list) -> tuple:
    """
    The same parser bug that splits one option in two also glues two options
    into one. Split `text` back into a pair at a sentence boundary.

    Prefer a boundary where the right-hand side opens the way the sibling
    options do (SQE1 answers overwhelmingly start 'Yes,' / 'No,'), since that
    is a far stronger signal than length. Fall back to the most balanced split.
    Returns (left, right) or (text, None) if no sane boundary exists.
    """
    parts = SENTENCE_END.split(text.strip())
    if len(parts) < 2:
        return text, None

    openers = tuple(w for w in ('Yes', 'No')
                    if sum(s.strip().startswith(w) for s in siblings) >= 2)

    best = None
    for i in range(1, len(parts)):
        left, right = ' '.join(parts[:i]).strip(), ' '.join(parts[i:]).strip()
        if len(left) < 25 or len(right) < 25:
            continue
        score = abs(len(left) - len(right))
        if openers and right.startswith(openers):
            score -= 10_000          # decisive preference
        if best is None or score < best[0]:
            best = (score, left, right)
    return (best[1], best[2]) if best else (text, None)


def repair_wrapped_options(questions):
    """
    Repair the option-wrap corruption: a wrapped option is split into two
    options, and — because the count must stay at five — the final two real
    options end up merged into one. Left alone this both scrambles the choices
    and points correct_index at the wrong text, which marks correct answers
    wrong. Runs before apply_overrides so overrides anchor on repaired text.

    Repair is structural and deterministic; where the answer becomes ambiguous
    the question is flagged rather than guessed, and can be pinned in
    answer_overrides.json.
    """
    repaired = ambiguous = 0
    for q in questions:
        opts = list(q.get('options') or [])
        if len(opts) < 2:
            continue
        key = q.get('correct_index')

        # 1. rejoin fragments into the option they were split from
        joined, key_map, changed = [], {}, False
        for i, o in enumerate(opts):
            if joined and _is_continuation(joined[-1], o):
                joined[-1] = joined[-1].rstrip() + ' ' + o.strip()
                key_map[i] = len(joined) - 1
                changed = True
            else:
                joined.append(o)
                key_map[i] = len(joined) - 1
        if not changed:
            continue

        new_key = key_map.get(key, key)

        # 2. one option now holds two — split the longest back apart
        if len(joined) < len(opts):
            longest = max(range(len(joined)), key=lambda i: len(joined[i]))
            left, right = _split_merged_option(
                joined[longest], [o for i, o in enumerate(joined) if i != longest])
            if right:
                joined[longest:longest + 1] = [left, right]
                if new_key == longest:
                    # the key pointed into the merged blob — which half is
                    # anyone's guess, so say so instead of picking one
                    ambiguous += 1
                    q['answer_ambiguous'] = True
                elif new_key is not None and new_key > longest:
                    new_key += 1

        q['options'] = joined
        if new_key is not None:
            q['correct_index'] = new_key
        q['options_repaired'] = True
        repaired += 1

    if repaired:
        _dbg(f"  [repair] rejoined wrapped options in {repaired} question(s)"
             + (f", {ambiguous} awaiting a pinned answer" if ambiguous else ""))
    return questions


def apply_overrides(questions, script_dir=None):
    """
    Apply manual answer corrections from answer_overrides.json.

    Each override matches a question by:
      • source_prefix   — question's 'source' field must start with this
      • question_prefix — question's 'question_text' must start with this

    The correct answer is then located by TEXT, not by index:
      • correct_text  — a distinctive substring of the option that is correct

    WHY TEXT AND NOT AN INDEX
    -------------------------
    Option ORDER is not stable. It changes whenever the parser is improved
    (e.g. when the option-merge bug is fixed and a merged option splits back
    into two) or when the source PDF is re-issued with reshuffled answers.
    A hardcoded 'correct_index' written against one parse silently points at a
    different option after the next parse — and because these overrides exist
    precisely to REJECT the plausible-but-wrong H5P answer, a stale index tends
    to land on exactly the option the override was written to rule out.

    On 2026-08-06 five of twelve index-based overrides were found doing this
    (roommates→"Tribunal", murder→"Magistrates' Court", new factory unit→
    "construction services are zero rated", new dwelling→"buyers not VAT
    registered", option to purchase→"no protectable interest").

    FAILURE BEHAVIOUR
    -----------------
    If correct_text matches zero options or more than one, the override is
    NOT applied and a loud warning is emitted. Leaving the H5P answer in place
    is bad; asserting a wrong answer with an authoritative override_note
    attached to it is worse, because it teaches the wrong rule with confidence.
    """
    if script_dir is None:
        script_dir = Path(__file__).parent
    overrides_path = Path(script_dir) / "answer_overrides.json"
    if not overrides_path.exists():
        _dbg(f"  [overrides] file not found: {overrides_path}")
        return questions

    try:
        with open(overrides_path, encoding="utf-8") as f:
            data = json.load(f)
        overrides = data.get("overrides", [])
    except Exception as e:
        _dbg(f"  [overrides] failed to load: {e}")
        return questions

    applied  = 0
    failures = []
    matched  = set()          # ids of overrides that found a question at all

    for q in questions:
        src  = q.get("source", "")
        qtxt = q.get("question_text", "")
        for oi, ov in enumerate(overrides):
            sp = ov.get("source_prefix", "")
            qp = ov.get("question_prefix", "")
            if not (src.startswith(sp) and _norm_opt(qtxt).startswith(_norm_opt(qp))):
                continue

            matched.add(oi)
            label   = f"{sp} | {qtxt[:55]!r}"
            old_idx = q.get("correct_index")
            opts    = q.get("options") or []
            ctext   = ov.get("correct_text")

            if ctext:
                needle = _norm_opt(ctext)
                hits   = [i for i, o in enumerate(opts) if needle in _norm_opt(o)]
                if len(hits) == 1:
                    new_idx = hits[0]
                elif not hits:
                    failures.append(f"{label}: correct_text {ctext!r} matches NO option "
                                    f"(options: {[o[:60] for o in opts]})")
                    break
                else:
                    failures.append(f"{label}: correct_text {ctext!r} is AMBIGUOUS — "
                                    f"matches options {hits}")
                    break
            elif isinstance(ov.get("correct_index"), int):
                # Legacy entry with no text anchor. Honour it, but say so —
                # it carries the staleness risk described above.
                new_idx = ov["correct_index"]
                failures.append(f"{label}: no correct_text, falling back to brittle "
                                f"correct_index={new_idx} — add a correct_text anchor")
            else:
                failures.append(f"{label}: override has neither correct_text nor correct_index")
                break

            if not 0 <= new_idx < len(opts):
                failures.append(f"{label}: resolved index {new_idx} out of range "
                                f"({len(opts)} options)")
                break

            q["correct_index"] = new_idx
            q["override_note"] = ov.get("note", "")
            # An override is a hand-verified answer, so it settles anything the
            # option-wrap repair had to flag as ambiguous. Clearing this is what
            # lets the question back into flashcards and normal marking.
            q.pop("answer_ambiguous", None)
            _dbg(f"  [override] {label}  cidx {old_idx}→{new_idx}  "
                 f"({opts[new_idx][:60]!r})")
            applied += 1
            break   # only one override per question

    for oi, ov in enumerate(overrides):
        if oi not in matched:
            failures.append(f"{ov.get('source_prefix','')} | "
                            f"{ov.get('question_prefix','')[:50]!r}: matched NO question "
                            f"— question text may have drifted, or it was deduped away")

    _dbg(f"  [overrides] applied {applied}/{len(overrides)} corrections")
    for f in failures:
        _dbg(f"  [overrides] !! {f}")
        print(f"WARNING [overrides] {f}", file=sys.stderr)

    return questions


def _topic_key(stem):
    """
    Return a canonical key for deduplication.
    e.g. 'COND3.2: Overview...' and 'COND3.2_ Overview...' → 'cond3.2'
    Matches the topic code prefix (letters + digits + dot/digit) at the start.
    """
    m = re.match(r'^([A-Za-z]+\d+(?:\.\d+)?)', stem)
    return m.group(1).lower() if m else stem.lower()


def parse_all(tests_dir, cache_file=None):
    """
    Parse all PDFs in tests_dir, deduplicate by topic key (keeping the most
    recently modified file per topic), apply overrides, and return all questions.

    Incremental cache: if cache_file is given (a Path or str), parsed results are
    stored per PDF keyed by filename and validated by file size.  On subsequent
    calls only PDFs whose size has changed are re-parsed; the rest are loaded
    from cache.  Keying by filename (not full path) and validating by size keeps
    the cache valid across environments (Mac vs sandbox) where paths and mtimes
    differ.  This makes re-runs after adding a single new PDF very fast.

    Cache format: JSON dict  { filename: {"mtime": float, "size": int, "questions": [...]} }
    """
    tests_dir = Path(tests_dir)
    all_pdfs = sorted(tests_dir.glob("*.pdf"))
    _dbg(f"Found {len(all_pdfs)} PDF files")

    # ── 1. Deduplicate: keep most-recently-modified file per topic ─────────
    seen = {}   # topic_key → Path
    for p in all_pdfs:
        key = _topic_key(p.stem)
        if key not in seen:
            seen[key] = p
        else:
            existing = seen[key]
            if p.stat().st_mtime > existing.stat().st_mtime:
                _dbg(f"  [dedup] replacing {existing.name} → {p.name}")
                seen[key] = p
            else:
                _dbg(f"  [dedup] keeping   {existing.name} (skipping {p.name})")

    pdfs = sorted(seen.values())
    _dbg(f"After dedup: {len(pdfs)} unique topics")

    # ── 2. Load incremental cache (if requested) ───────────────────────────
    cache = {}
    if cache_file is not None:
        cache_file = Path(cache_file)
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
                _dbg(f"Cache loaded: {len(cache)} entries from {cache_file.name}")
            except Exception as e:
                _dbg(f"Cache load error (ignored): {e}")
                cache = {}

    # ── 3. Parse each unique PDF (skip if cached and unchanged) ──────
    # Cache key is the bare filename (NOT the full path) so a cache built in
    # one environment (e.g. the user's Mac) stays valid in another (e.g. the
    # Cowork sandbox, whose mount path changes every session).  Validation is
    # by file SIZE, which is stable across environments; mtime is only used as
    # a fallback for legacy cache entries that predate size tracking.
    all_q = []
    cache_hits = 0
    cache_misses = 0
    for p in pdfs:
        st = p.stat()
        mtime, size = st.st_mtime, st.st_size
        cache_key = p.name
        cached = cache.get(cache_key)

        if cached and (
            (cached.get("size") is not None and cached.get("size") == size)
            or (cached.get("size") is None and abs(cached.get("mtime", 0) - mtime) < 1.0)
        ):
            # Cache hit — reuse previously parsed questions
            qs = cached["questions"]
            cache_hits += 1
            _dbg(f"  {len(qs):3d} q  [CACHED]  {p.name}")
        else:
            # Cache miss — re-parse
            subject, paper = subject_from_filename(p.name)
            if p.stem.upper().startswith("SLK"):
                qs = parse_canvas_pdf(str(p), subject, paper)
            else:
                qs = parse_pdf(str(p), subject, paper)
            cache[cache_key] = {"mtime": mtime, "size": size, "questions": qs}
            cache_misses += 1
            _dbg(f"  {len(qs):3d} q  [{paper:4s} / {subject}]  {p.name}")
            # Persist incrementally so progress survives interrupted runs
            # (e.g. sandbox timeouts) instead of only saving at the very end.
            if cache_file is not None:
                try:
                    cache_file.write_text(
                        json.dumps(cache, ensure_ascii=False), encoding="utf-8"
                    )
                except Exception:
                    pass

        all_q.extend(qs)

    _dbg(f"Cache: {cache_hits} hits, {cache_misses} misses")

    # ── 4. Persist updated cache ───────────────────────────────────────────
    if cache_file is not None:
        try:
            cache_file.write_text(
                json.dumps(cache, ensure_ascii=False), encoding="utf-8"
            )
            _dbg(f"Cache saved: {len(cache)} entries → {cache_file.name}")
        except Exception as e:
            _dbg(f"Cache save error (ignored): {e}")

    all_q = repair_wrapped_options(all_q)
    all_q = apply_overrides(all_q)

    # Anything still ambiguous after overrides is genuinely unresolved: it is
    # excluded from mistake flashcards, so surface it rather than let it sit.
    still = [q for q in all_q if q.get("answer_ambiguous")]
    if still:
        _dbg(f"  [repair] {len(still)} question(s) still need an answer pinned "
             f"in answer_overrides.json:")
        for q in still:
            _dbg(f"      {q.get('source','?')[:34]} | {q.get('question_text','')[:60]}")
    else:
        _dbg("  [repair] no unresolved answers")

    # ── 5. Question-level dedup (mock exam bank only) ──────────────────────
    # Each question must appear ONCE in a mock exam. File-level dedup (step 1)
    # misses re-sit files whose names start with a digit ("10.2 v2.pdf",
    # "8.5 v2.pdf") or lack the topic code ("CRM 5.3.pdf"), because _topic_key
    # requires letters-then-digits and falls back to the whole stem.
    #
    # Deliberately question-level, NOT file-level: those re-sit files also
    # contain questions found nowhere else (e.g. "9.4 v2 0508" has 7 unique).
    # Dropping whole files would lose them. Keyed on normalised question text
    # so wording-identical repeats collapse regardless of option order.
    #
    # This does NOT affect flashcards: extract_mistakes.load_h5p_wrong_answers
    # globs the PDFs itself and applies no dedup, so wrong answers from every
    # sitting of every file are still captured.
    #
    # Matching on the stem ALONE is wrong: PROP12.7 contains two genuinely
    # different questions sharing a word-for-word identical stem ("...subscribes
    # to the UK Finance Mortgage Lenders' Handbook. Which one of the following is
    # one of the requirements set out in the Handbook?"). Their option sets are
    # disjoint and their answers differ — they are two real questions, and a
    # stem-only rule silently deletes one.
    #
    # So: same stem AND some evidence the answer is the same. Evidence is either
    # an overlapping option or a matching correct answer — either alone suffices,
    # because both drift between sittings:
    #   • options are reshuffled, so index means nothing
    #   • wording drifts ("committed to" vs "sent to the Crown Court",
    #     "7 years" vs "seven years")
    #   • the correct answer can be abbreviated ("COLP" vs "compliance officer
    #     for legal practice"), which defeats an answer-text test on its own
    #   • the PDF parser truncates options mid-word, which defeats exact equality
    # Comparing 40-char prefixes absorbs the truncation and most of the drift.
    #
    # Stems are compared on their first 150 chars for the same reason — trailing
    # drift (a curly vs straight apostrophe, a reworded final sentence) otherwise
    # splits a genuine repeat into two.
    def _norm(s):
        return re.sub(r'\W+', '', (s or '').lower())

    def _opt_set(q):
        return {_norm(o)[:40] for o in (q.get('options') or []) if _norm(o)}

    def _answer(q):
        opts, ci = q.get('options') or [], q.get('correct_index')
        if not isinstance(ci, int) or not 0 <= ci < len(opts):
            return ''                    # unanswered / unparsed — no evidence
        return _norm(opts[ci])[:40]

    by_stem = defaultdict(list)      # stem prefix -> [(opt_set, answer)]
    deduped = []
    for q in all_q:
        stem = _norm(q.get('question_text'))[:150]
        opts, ans = _opt_set(q), _answer(q)
        is_repeat = False
        for prev_opts, prev_ans in by_stem[stem]:
            if not opts or not prev_opts:
                is_repeat = True                      # nothing to compare on
            else:
                is_repeat = bool(opts & prev_opts) or (ans and ans == prev_ans)
            if is_repeat:
                break
        if is_repeat:
            continue
        by_stem[stem].append((opts, ans))
        deduped.append(q)

    if len(deduped) != len(all_q):
        _dbg(f"  [dedup] question-level: {len(all_q)} → {len(deduped)} "
             f"({len(all_q) - len(deduped)} repeat(s) removed)")
    return deduped


if __name__ == "__main__":
    tests_dir = (sys.argv[1] if len(sys.argv) > 1
                 else str(Path(__file__).parent / "Tests"))
    if not os.path.isdir(tests_dir):
        _dbg(f"ERROR: not found: {tests_dir}")
        sys.exit(1)
    questions = parse_all(tests_dir)
    _dbg(f"\nTotal questions parsed: {len(questions)}")
    print(json.dumps(questions, ensure_ascii=False, indent=2))
