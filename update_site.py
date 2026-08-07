#!/usr/bin/env python3
"""
SQE1 Site Updater
─────────────────
Run this whenever you add new question PDFs to the Tests folder.
It will: parse questions → rebuild the standalone exam HTML → push to GitHub.

Usage: python3 update_site.py
"""

import sys, os, json, subprocess, re, base64
from ftplib import FTP, all_errors as FTP_ERRORS
from pathlib import Path
try:
    import urllib.request as _urllib
except ImportError:
    _urllib = None

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

GITHUB_REPO = "rfn2jk9dw9-max/SQE-Prep"
GITHUB_BRANCH = "main"

def _load_github_token():
    """Load GitHub PAT from secrets.json next to this script."""
    secrets_path = SCRIPT_DIR / "secrets.json"
    if secrets_path.exists():
        try:
            data = json.loads(secrets_path.read_text())
            return data.get("github_token", "")
        except Exception:
            pass
    return os.environ.get("GITHUB_TOKEN", "")

def _load_ftp_creds():
    """Load Hostinger FTP settings from secrets.json (falls back to defaults).
    secrets.json may contain an "ftp" object, e.g.:
      "ftp": {"host": "82.112.243.57", "port": 21,
              "user": "u256011742.solicitor", "password": "...",
              "dir": "solicitor"}
    """
    # NOTE: no password default here on purpose. Credentials belong in
    # secrets.json (gitignored), never in a tracked source file.
    defaults = {"host": "82.112.243.57", "port": 21,
                "user": "u256011742.solicitor", "password": "",
                "dir": "solicitor"}
    secrets_path = SCRIPT_DIR / "secrets.json"
    if secrets_path.exists():
        try:
            data = json.loads(secrets_path.read_text())
            defaults.update(data.get("ftp", {}) or {})
        except Exception:
            pass
    if not defaults.get("password"):
        print("  ⚠ No FTP password found. Add it to secrets.json under "
              '"ftp": {"password": "..."} to enable Hostinger upload.')
    return defaults

def _github_api(method, path, payload=None, token=""):
    """Minimal GitHub REST API caller (no third-party deps)."""
    url = f"https://api.github.com{path}"
    data = json.dumps(payload).encode() if payload else None
    req = _urllib.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")
    try:
        with _urllib.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), None
    except Exception as e:
        return None, str(e)

def github_push_files(files_dict, commit_message, token):
    """
    Push multiple files to GitHub via the Contents API.
    files_dict: {filename: Path_or_bytes}
    Returns (success, message).
    """
    if not token:
        return False, "No GitHub token found in secrets.json"

    pushed, errors = [], []
    for filename, source in files_dict.items():
        content_bytes = source.read_bytes() if isinstance(source, Path) else source
        b64 = base64.b64encode(content_bytes).decode()

        # Get current SHA (needed for updates)
        info, err = _github_api("GET", f"/repos/{GITHUB_REPO}/contents/{filename}?ref={GITHUB_BRANCH}", token=token)
        sha = info["sha"] if info and "sha" in info else None

        payload = {"message": commit_message, "content": b64, "branch": GITHUB_BRANCH}
        if sha:
            payload["sha"] = sha

        result, err = _github_api("PUT", f"/repos/{GITHUB_REPO}/contents/{filename}", payload=payload, token=token)
        if result and "content" in result:
            pushed.append(filename)
        else:
            errors.append(f"{filename}: {err}")

    if errors:
        return False, f"Errors: {'; '.join(errors)}"
    return True, f"Pushed {len(pushed)} file(s): {', '.join(pushed)}"

def git_publish(commit_message):
    """Publish via LOCAL git so there is a single, linear history.

    Root cause of the recurring merge conflicts: this script used to push via
    the GitHub Contents API (server-side commits) while manual edits went
    through local git, so the two histories diverged and collided on the
    single-line data files. Publishing through git instead keeps origin and
    local in lockstep — both the daily job and manual edits run on this Mac
    and share this repo, so local is always ahead-or-equal to origin and a
    plain push succeeds.

    Also clears stale .git lock files left by crashed runs (the other thing
    that jammed us), commits pending changes, resyncs with origin, and pushes.

    Returns (ok, message). In the Cowork sandbox git is unavailable, so this
    returns (False, ...) and the caller falls back to the API push.
    """
    if IN_SANDBOX:
        return False, "sandbox — git unavailable, using API"

    repo = str(SCRIPT_DIR)
    def g(args):
        return subprocess.run(f"git {args}", shell=True, cwd=repo,
                              capture_output=True, text=True)

    if g("rev-parse --is-inside-work-tree").returncode != 0:
        return False, "not a git repository"

    # 1. clear stale locks from a crashed git/editor (prevents index.lock hangs)
    for lock in ("index.lock", "HEAD.lock"):
        try:
            (SCRIPT_DIR / ".git" / lock).unlink()
        except OSError:
            pass

    # 2. stage + commit local changes (generated files + any manual note edits)
    g("add -A")
    if g("diff --cached --quiet").returncode != 0:
        g(f'commit -m "{commit_message}"')

    # 3. auto-resync with origin, then push
    g("fetch origin main")
    if g("rebase origin/main").returncode != 0:
        # conflict (usually the single-line data files): keep our freshly
        # generated/edited version rather than aborting into a broken state.
        g("rebase --abort")
        g("merge -X ours --no-edit origin/main")
    # 4. push. Authenticate with the token from secrets.json rather than a
    #    token baked into the remote URL — that keeps .git/config free of
    #    secrets, so a shared folder or screenshot can't leak it. Fetching
    #    needs no auth because the repo is public.
    token = _load_github_token()
    if token:
        owner = GITHUB_REPO.split("/")[0]
        push_url = f"https://{owner}:{token}@github.com/{GITHUB_REPO}.git"
        push = g(f'push "{push_url}" HEAD:{GITHUB_BRANCH}')
    else:
        push = g("push origin main")
    ok = push.returncode == 0
    tail = (push.stdout + push.stderr).strip().splitlines()
    msg = tail[-1] if tail else ("pushed" if ok else "push failed")
    # never surface the token if git echoes the URL back in an error
    if token:
        msg = msg.replace(token, "<token>")
    return ok, msg

def git_publish_sandbox(commit_message, files):
    """Publish from inside the Cowork sandbox.

    Why not plain git on the repo, or the GitHub API?
      • The sandbox mounts the iCloud repo on a filesystem that FORBIDS
        deleting files. git constantly creates/removes lock files
        (index.lock, ref .lock, tmp objects), so any git op against the
        mounted .git leaves un-removable locks and wedges the repo.
      • api.github.com is blocked by the sandbox proxy (403 Forbidden), so
        the Contents-API fallback can't reach GitHub either.

    Solution: git-https to github.com IS reachable. So we clone a fresh
    working copy into the sandbox-local /tmp (which DOES allow deletes),
    copy the freshly generated files in, commit and push from there. The
    mounted .git is never touched, so nothing gets wedged.

    files: {filename: Path_on_mount}. Returns (ok, message).
    """
    import tempfile, shutil
    token = _load_github_token()
    if not token:
        return False, "no GitHub token in secrets.json"
    owner = GITHUB_REPO.split("/")[0]
    url = f"https://{owner}:{token}@github.com/{GITHUB_REPO}.git"
    work = tempfile.mkdtemp(prefix="sqe_push_")
    repo = os.path.join(work, "repo")
    def g(args, cwd=repo):
        return subprocess.run(f"git {args}", shell=True, cwd=cwd,
                              capture_output=True, text=True)
    try:
        clone = subprocess.run(
            f'git clone --depth 1 -b {GITHUB_BRANCH} "{url}" "{repo}"',
            shell=True, capture_output=True, text=True, timeout=120)
        if clone.returncode != 0:
            return False, "clone failed: " + (clone.stderr.strip().splitlines()[-1] if clone.stderr.strip() else "unknown")
        for name, src in files.items():
            try:
                shutil.copyfile(str(src), os.path.join(repo, name))
            except Exception as e:
                return False, f"copy {name} failed: {e}"
        g('config user.email "auto@sqe1"')
        g('config user.name "SQE1 Auto"')
        g("add -A")
        if g("diff --cached --quiet").returncode == 0:
            return True, "no changes to publish (origin already current)"
        c = g(f'commit -m "{commit_message}"')
        if c.returncode != 0:
            return False, "commit failed: " + (c.stderr or c.stdout).strip()
        push = g(f"push origin HEAD:{GITHUB_BRANCH}")
        if push.returncode != 0:
            tail = (push.stdout + push.stderr).strip().splitlines()
            return False, "push failed: " + (tail[-1] if tail else "unknown")
        return True, "pushed via sandbox clone"
    finally:
        try:
            shutil.rmtree(work, ignore_errors=True)
        except Exception:
            pass

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
    cache_file = SCRIPT_DIR / "_parse_cache.json"
    questions = parse_questions.parse_all(str(TESTS_DIR), cache_file=cache_file)
    print(f"  ✓ {len(questions)} questions parsed")

    # ── 2. Rebuild standalone HTML ────────────────────────────
    # IMPORTANT: only the COLP bank (QUESTION_BANK) is refreshed from the
    # Tests PDFs. SRA_BANK (SRA Sample) and REVISE_BANK (Revise SQE) must
    # NEVER be touched by the daily update — so we edit the standalone
    # in place rather than rebuilding it from the SQE1_MockExam.html
    # template (which would clobber the standalone's SRA/Revise banks
    # with the template's copies).
    print(f"\n[2/4] Updating COLP question bank in standalone HTML...")
    if STANDALONE.exists():
        html = STANDALONE.read_text(encoding='utf-8')
    else:
        print(f"  ℹ Standalone not found — bootstrapping from template {MOCK_SRC.name}")
        html = MOCK_SRC.read_text(encoding='utf-8')

    # Replace ONLY the embedded COLP question bank (safe even if already updated)
    qbank_js = json.dumps(questions, ensure_ascii=False).replace("</script>", "<\\/script>")
    html, n = re.subn(
        r'const QUESTION_BANK = \[.*?\];',
        f'const QUESTION_BANK = {qbank_js};',
        html,
        count=1,
        flags=re.DOTALL
    )
    if n:
        print(f"  ✓ QUESTION_BANK (COLP) replaced ({len(questions)} questions)")
        print(f"  ✓ SRA_BANK and REVISE_BANK left untouched")
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

    # ── 2b. Inject personal mistakes into revision guide FLASHCARDS ──
    # (Mistakes belong in the flip-card flashcard deck, NOT woven into the
    # chapter notes prose — see extract_mistakes.inject_mistake_flashcards.)
    print(f"\n[2b/4] Injecting personal mistake flashcards into revision guide...")
    hy_standalone = SCRIPT_DIR / "SQE1_HighYield_Standalone.html"
    if hy_standalone.exists():
        try:
            from extract_mistakes import get_personal_mistake_flashcards, inject_mistake_flashcards
            by_key = get_personal_mistake_flashcards(TESTS_DIR, SCRIPT_DIR / "progress.json",
                                                     cache_file=cache_file, bank=questions)
            if by_key:
                hy_html = hy_standalone.read_text(encoding='utf-8')
                hy_html = inject_mistake_flashcards(hy_html, by_key)
                hy_standalone.write_text(hy_html, encoding='utf-8')
                print(f"  ✓ Revision guide flashcards updated with personal mistakes")
            else:
                print(f"  ℹ No wrong answers mapped to flashcard decks yet")
        except Exception as e:
            print(f"  ⚠ Could not inject mistake flashcards: {e}")
    else:
        print(f"  ⚠ SQE1_HighYield_Standalone.html not found")

    # ── 2c. Upload progress.php to Hostinger via FTP ──────────
    print(f"\n[2c/4] Uploading progress.php to Hostinger...")
    if IN_SANDBOX:
        print(f"  ℹ Skipped in sandbox (no outbound FTP). Run locally to upload.")
    else:
        # Upload the API files. These must NOT contain credentials — they read
        # them from db_config.php, which lives outside the web root and is
        # uploaded manually, never by this script.
        php_files = [SCRIPT_DIR / n for n in
                     ("_db_connect.php", "progress.php", "colp_progress.php")]
        php_files = [p for p in php_files if p.exists()]
        leaky = [p.name for p in php_files if "DB_PASS" in p.read_text(errors="ignore")]
        if leaky:
            print(f"  ⚠ Refusing to upload {', '.join(leaky)} — still contains "
                  f"hardcoded credentials. Use the patched version.")
            php_files = [p for p in php_files if p.name not in leaky]
        if php_files:
            creds = _load_ftp_creds()
            try:
                ftp = FTP()
                ftp.connect(creds["host"], int(creds.get("port", 21)), timeout=15)
                ftp.login(creds["user"], creds["password"])
                if creds.get("dir"):
                    try:
                        ftp.cwd(creds["dir"])
                    except Exception:
                        pass
                for p in php_files:
                    with open(p, 'rb') as f:
                        ftp.storbinary(f'STOR {p.name}', f)
                    print(f"  ✓ {p.name} uploaded to Hostinger")
                ftp.quit()
            except FTP_ERRORS as e:
                print(f"  ⚠ FTP upload failed: {e}")
                if "530" in str(e):
                    print(f"    → 530 = login rejected. Refresh the FTP username/password")
                    print(f"      in Hostinger (hPanel → Files → FTP Accounts), then update")
                    print(f"      the \"ftp\" block in secrets.json.")
        else:
            print(f"  ⚠ progress.php not found")

    # ── 3 & 4. Publish ────────────────────────────────────────
    # Prefer LOCAL git (single linear history — avoids the API-vs-git
    # divergence that used to cause the recurring conflicts). Fall back to the
    # GitHub API only in the sandbox or if git is unavailable.
    print(f"\n[3/4] Publishing to GitHub...")
    commit_msg = f"Update: {len(questions)} questions embedded"

    files_to_push = {
        "SQE1_MockExam_Standalone.html": STANDALONE,
        "SQE1_HighYield_Standalone.html": SCRIPT_DIR / "SQE1_HighYield_Standalone.html",
    }
    index_html = SCRIPT_DIR / "index.html"
    if index_html.exists():
        files_to_push["index.html"] = index_html

    if IN_SANDBOX:
        # Mount forbids deletes (wedges local git) and api.github.com is
        # proxy-blocked — so publish from a throwaway clone on /tmp instead.
        print(f"\n[4/4] Publishing {len(files_to_push)} file(s) via sandbox clone...")
        ok, msg = git_publish_sandbox(commit_msg, files_to_push)
        print(f"  {'✓' if ok else '✗'} {msg}")
    else:
        ok, msg = git_publish(commit_msg)
        if ok:
            print(f"  ✓ Published via git: {msg}")
        else:
            print(f"  ℹ git publish unavailable ({msg}); trying GitHub API...")
            token = _load_github_token()
            if not token:
                print(f"  ⚠ No GitHub token — skipping push.")
                print(f"  → Add your token to secrets.json: {{\"github_token\": \"ghp_...\"}}")
            else:
                print(f"\n[4/4] Committing {len(files_to_push)} file(s) via API...")
                ok, msg = github_push_files(files_to_push, commit_msg, token)
                print(f"  {'✓' if ok else '✗'} {msg}")

    if ok:
        print(f"\n✓ Done! Site updated at:")
        print(f"  https://rfn2jk9dw9-max.github.io/SQE-Prep/")
    print("=" * 55)

if __name__ == "__main__":
    main()
