#!/usr/bin/env python3
"""
SQE1 Site Updater
─────────────────
Run this whenever you add new question PDFs to the Tests folder.
It will: parse questions → rebuild the standalone exam HTML → push to GitHub.

Usage: python3 update_site.py
"""

import sys, os, json, subprocess, re
from pathlib import Path

SCRIPT_DIR  = Path('/Users/ghitab/Documents/Claude/Projects/Mission solicitor')
TESTS_DIR   = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/Tests"
MOCK_SRC    = SCRIPT_DIR / "SQE1_MockExam.html"
STANDALONE  = SCRIPT_DIR / "SQE1_MockExam_Standalone.html"

def run(cmd, **kw):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    if result.stdout.strip(): print(result.stdout.strip())
    if result.stderr.strip(): print(result.stderr.strip())
    return result.returncode

def main():
    print("=" * 55)
    print("  SQE1 Site Updater")
    print("=" * 55)

    # ── 1. Parse questions ────────────────────────────────────
    print(f"\n[1/4] Parsing questions from: {TESTS_DIR}")
    if not TESTS_DIR.exists():
        print(f"  ✗ Tests folder not found at expected location.")
        print(f"    Check: {TESTS_DIR}")
        sys.exit(1)

    sys.path.insert(0, str(SCRIPT_DIR))
    import parse_questions
    questions = parse_questions.parse_all(str(TESTS_DIR))
    print(f"  ✓ {len(questions)} questions parsed")

    # ── 2. Rebuild standalone HTML ────────────────────────────
    print(f"\n[2/4] Rebuilding standalone HTML...")
    html = MOCK_SRC.read_text(encoding='utf-8')

    SHIM = f"""// ── STANDALONE MODE ──────────────────────────────────────
const EMBEDDED_QUESTIONS = {json.dumps(questions)};
const PROGRESS_API = 'https://bidouillecode.dev/solicitor/progress.php';
async function lsGetProgress(){{
  try{{const r=await fetch(PROGRESS_API);if(r.ok)return await r.json();}}catch(e){{}}
  try{{return JSON.parse(localStorage.getItem('sqe1_progress_v1')||'[]');}}catch(e){{return[];}}
}}
async function lsSaveProgress(s){{
  try{{await fetch(PROGRESS_API,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(s)}});}}catch(e){{}}
  try{{const a=JSON.parse(localStorage.getItem('sqe1_progress_v1')||'[]');a.push(s);localStorage.setItem('sqe1_progress_v1',JSON.stringify(a));}}catch(e){{}}
}}
async function lsDeleteProgress(dt){{
  try{{await fetch(PROGRESS_API,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{delete_datetime:dt}})}});}}catch(e){{}}
  try{{const a=JSON.parse(localStorage.getItem('sqe1_progress_v1')||'[]').filter(s=>s.datetime!==dt);localStorage.setItem('sqe1_progress_v1',JSON.stringify(a));}}catch(e){{}}
}}
// ─────────────────────────────────────────────────────────
"""

    replacements = [
        ("const API = 'http://127.0.0.1:4321';",
         SHIM + "const API = 'http://127.0.0.1:4321'; // unused in standalone"),

        ("const res = await fetch(`${API}/api/questions`);\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    const data = await res.json();\n    if (!Array.isArray(data) || data.length === 0)\n      throw new Error('Empty question bank returned');\n    QUESTION_BANK = data;",
         "const data = EMBEDDED_QUESTIONS;\n    if (!Array.isArray(data) || data.length === 0)\n      throw new Error('Empty question bank returned');\n    QUESTION_BANK = data;"),

        ("const pr = await fetch(`${API}/api/progress`);\n      if (pr.ok) SESSION_HISTORY = await pr.json();",
         "SESSION_HISTORY = await lsGetProgress();"),

        ("const res=await fetch(`${API}/api/progress`,{\n      method:'POST',headers:{'Content-Type':'application/json'},\n      body:JSON.stringify(result)\n    });\n    if (!res.ok) console.warn('Save progress HTTP',res.status);\n    else SESSION_HISTORY.push(result);  // keep in-memory history current for next session",
         "await lsSaveProgress(result);\n    SESSION_HISTORY.push(result);"),

        ("const res=await fetch(`${API}/api/progress`);\n    if (!res.ok) throw new Error(`HTTP ${res.status}`);\n    const sessions=await res.json();\n    renderDashboard(sessions);",
         "const sessions=await lsGetProgress();\n    renderDashboard(sessions);"),

        ("const res = await fetch(`${API}/api/progress/delete`, {\n      method: 'POST',\n      headers: {'Content-Type':'application/json'},\n      body: JSON.stringify({datetime: dt})\n    });\n    if (!res.ok) throw new Error('HTTP ' + res.status);",
         "await lsDeleteProgress(dt);"),

        ('<h2>Connecting to SQE1 Server…</h2>\n    <p>Parsing you',
         '<h2>Loading questions…</h2>\n    <p>Setting you'),

        ('Setting your question bank from the Tests folder.',
         f'Preparing your {len(questions)} questions.'),

        ('<h2>⚠ SQE1 Server Not Running</h2>\n    <p>The local SQE1 server is not running.<br>\n    Please open Cowork to restart it, then refresh this page.<br><br>\n    <small style="color:#999">Trying http://127.0.0.1:4321</small></p>',
         '<h2>⚠ Could not load questions</h2>\n    <p>Please try refreshing the page.</p>'),
    ]

    ok = 0
    for old, new in replacements:
        if old in html:
            html = html.replace(old, new, 1)
            ok += 1
        else:
            print(f"  ⚠ Pattern not found (may already be replaced): {old[:50].strip()}")

    STANDALONE.write_text(html, encoding='utf-8')
    print(f"  ✓ Standalone HTML rebuilt ({len(html):,} chars, {ok}/{len(replacements)} replacements)")

    # ── 2b. Inject personal mistake notes into revision guide ─
    print(f"\n[2b/4] Injecting personal mistake notes into revision guide...")
    hy_standalone = SCRIPT_DIR / "SQE1_HighYield_Standalone.html"
    if hy_standalone.exists():
        try:
            from extract_mistakes import get_personal_notes, inject_personal_notes
            TESTS_DIR_PATH = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/Tests"
            by_chapter = get_personal_notes(TESTS_DIR_PATH, SCRIPT_DIR / "progress.json")
            if by_chapter:
                hy_html = hy_standalone.read_text(encoding='utf-8')
                hy_html = inject_personal_notes(hy_html, by_chapter)
                hy_standalone.write_text(hy_html, encoding='utf-8')
                print(f"  ✓ Revision guide updated with personal notes")
            else:
                print(f"  ℹ No wrong answers mapped to chapters yet")
        except Exception as e:
            print(f"  ⚠ Could not inject personal notes: {e}")
    else:
        print(f"  ⚠ SQE1_HighYield_Standalone.html not found")

    # ── 3. Stage & commit ─────────────────────────────────────
    print(f"\n[3/4] Committing to git...")
    os.chdir(SCRIPT_DIR)
    run("git add SQE1_MockExam_Standalone.html index.html SQE1_HighYield_Standalone.html progress.php")
    run(f'git commit -m "Update: {len(questions)} questions embedded"')

    # ── 4. Push to GitHub ─────────────────────────────────────
    print(f"\n[4/4] Pushing to GitHub...")
    code = run("git push origin main")
    if code == 0:
        print(f"\n✓ Done! Site updated at:")
        print(f"  https://rfn2jk9dw9-max.github.io/SQE-Prep/")
    else:
        print(f"\n✗ Push failed — check your GitHub credentials.")

    print("=" * 55)

if __name__ == "__main__":
    main()
