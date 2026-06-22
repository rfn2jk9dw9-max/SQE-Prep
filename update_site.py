#!/usr/bin/env python3
"""
SQE1 Site Updater
─────────────────
Run this whenever you add new question PDFs to the Tests folder.
It will: parse questions → rebuild the standalone exam HTML → push to GitHub.

Usage: python3 update_site.py
"""

import sys, os, json, subprocess, re
from ftplib import FTP, all_errors as FTP_ERRORS
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────
# Supports running on the user's Mac OR inside the Cowork sandbox.
# The sandbox mounts iCloud at a different path, so we probe both.
def _find_session_mounts():
    """Dynamically find any active Cowork session mount paths."""
    sessions_root = Path('/sessions')
    icloud_paths, script_paths = [], []
    if sessions_root.exists():
        try:
            for session in sessions_root.iterdir():
                mnt = session / 'mnt'
                icloud_paths.append(mnt / 'Formation Solicitor' / 'Tests')
                script_paths.append(mnt / 'Mission solicitor')
        except PermissionError:
            pass
    return icloud_paths, script_paths

_dyn_icloud, _dyn_script = _find_session_mounts()

_ICLOUD_CANDIDATES = [
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/Tests",
] + _dyn_icloud

_SCRIPT_CANDIDATES = [
    Path('/Users/ghitab/Documents/Claude/Projects/Mission solicitor'),
] + _dyn_script

def _safe_exists(p):
    try:
        return p.exists()
    except PermissionError:
        return False

SCRIPT_DIR = next((p for p in _SCRIPT_CANDIDATES if _safe_exists(p)), _SCRIPT_CANDIDATES[0])
TESTS_DIR  = next((p for p in _ICLOUD_CANDIDATES if _safe_exists(p)), _ICLOUD_CANDIDATES[0])

# In sandbox, git operations always fail (lock-file permissions).
IN_SANDBOX = str(Path.home()).startswith('/sessions/')

MOCK_SRC   = SCRIPT_DIR / "SQE1_MockExam.html"
STANDALONE = SCRIPT_DIR / "SQE1_MockExam_Standalone.html"

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

    # Replace the embedded question bank directly (safe even if already updated)
    qbank_js = json.dumps(questions, ensure_ascii=False).replace("</script>", "<\\/script>")
    html, n = re.subn(
        r'const QUESTION_BANK = \[.*?\];',
        f'const QUESTION_BANK = {qbank_js};',
        html,
        count=1,
        flags=re.DOTALL
    )
    if n:
        print(f"  ✓ QUESTION_BANK replaced ({len(questions)} questions)")
    else:
        print(f"  ⚠ QUESTION_BANK pattern not found — standalone may already be current")

    # Ensure deleteSession is correctly async (guard against regression)
    broken = (
        'function deleteSession(dt) {\n  if (!confirm("Delete this session?")) return;\n  try {\n'
        '    await lsDeleteProgress(dt);\n    const sessions = await lsGetProgress();\n    renderDashboard(sessions);\n'
        '  } catch(e) { alert("Could not delete session."); }\n}'
    )
    fixed = (
        'async function deleteSession(dt) {\n  if (!confirm("Delete this session?")) return;\n  try {\n'
        '    await fetch(PROGRESS_API, {method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({delete_datetime:dt})});\n'
        '    const sessions = await fetchSessions();\n    renderDashboard(sessions);\n'
        '  } catch(e) { alert("Could not delete session."); }\n}'
    )
    if broken in html:
        html = html.replace(broken, fixed, 1)
        print(f"  ✓ deleteSession async regression fixed")

    STANDALONE.write_text(html, encoding='utf-8')
    print(f"  ✓ Standalone HTML written ({len(html):,} chars)")

    # ── 2b. Inject personal mistake notes into revision guide ─
    print(f"\n[2b/4] Injecting personal mistake notes into revision guide...")
    hy_standalone = SCRIPT_DIR / "SQE1_HighYield_Standalone.html"
    if hy_standalone.exists():
        try:
            from extract_mistakes import get_personal_notes, inject_personal_notes
            by_chapter = get_personal_notes(TESTS_DIR, SCRIPT_DIR / "progress.json")
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

    # ── 2c. Upload progress.php to Hostinger via FTP ──────────
    print(f"\n[2c/4] Uploading progress.php to Hostinger...")
    if IN_SANDBOX:
        print(f"  ℹ Skipped in sandbox (no outbound FTP). Run locally to upload.")
    else:
        php_file = SCRIPT_DIR / "progress.php"
        if php_file.exists():
            try:
                ftp = FTP()
                ftp.connect('82.112.243.57', 21, timeout=15)
                ftp.login('u256011742.solicitor', '#Patience13#')
                try:
                    ftp.cwd('solicitor')
                except Exception:
                    pass
                with open(php_file, 'rb') as f:
                    ftp.storbinary('STOR progress.php', f)
                ftp.quit()
                print(f"  ✓ progress.php uploaded to Hostinger")
            except FTP_ERRORS as e:
                print(f"  ⚠ FTP upload failed: {e}")
        else:
            print(f"  ⚠ progress.php not found")

    # ── 3. Stage & commit ─────────────────────────────────────
    print(f"\n[3/4] Committing to git...")
    if IN_SANDBOX:
        print(f"  ℹ Skipped in sandbox (git lock-file restriction).")
        print(f"  → Run locally: git add SQE1_MockExam_Standalone.html SQE1_HighYield_Standalone.html && git commit -m 'Update: {len(questions)} questions' && git push origin main")
    else:
        os.chdir(SCRIPT_DIR)
        # Clear any stale lock files before committing
        for lock in ['.git/HEAD.lock', '.git/index.lock', '.git/objects/maintenance.lock',
                     '.git/refs/remotes/origin/main.lock']:
            lock_path = SCRIPT_DIR / lock
            if lock_path.exists():
                lock_path.unlink(missing_ok=True)
        run("git add SQE1_MockExam_Standalone.html index.html SQE1_HighYield_Standalone.html progress.php")
        run(f'git commit -m "Update: {len(questions)} questions embedded"')

        # ── 4. Push to GitHub ──────────────────────────────────
        print(f"\n[4/4] Pushing to GitHub...")
        # Pull first to avoid non-fast-forward rejection
        run("git stash")
        run("git pull origin main --rebase")
        run("git stash pop")
        code = run("git push origin main")
        if code == 0:
            print(f"\n✓ Done! Site updated at:")
            print(f"  https://rfn2jk9dw9-max.github.io/SQE-Prep/")
        else:
            print(f"\n✗ Push failed — check your GitHub credentials.")

    print("=" * 55)

if __name__ == "__main__":
    main()
