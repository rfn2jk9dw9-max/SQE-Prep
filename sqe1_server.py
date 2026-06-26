#!/usr/bin/env python3
"""
SQE1 Local Server  —  http://127.0.0.1:4321
─────────────────────────────────────────────
GET  /          → mock exam page
GET  /test      → mock exam page
GET  /guide     → revision guide
GET  /api/questions  → parse Tests folder, return JSON array
GET  /api/progress   → read progress.json
POST /api/progress   → append session result to progress.json

Run:  python3 sqe1_server.py
Stop: Ctrl-C
POST /api/annotate  → proxy to Anthropic Claude API (annotation helper)
"""

import sys, os, json, logging, hashlib, time, signal
import urllib.request, urllib.error
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Ignore SIGPIPE so broken-pipe errors from launchd's stderr pipe
# don't kill the server or propagate into the question parser.
signal.signal(signal.SIGPIPE, signal.SIG_IGN)

# ── Paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent   # …/Mission solicitor/
PORT = 4321
HOST = "127.0.0.1"


def _find_dir_in_icloud(name):
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
    if not icloud.exists():
        return None
    hits = sorted(icloud.glob(f"**/{name}"))
    return hits[0] if hits else None


def find_tests_dir():
    # 1. Exact known iCloud path (fastest, most reliable)
    exact = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/Tests"
    if exact.exists():
        return exact
    # 2. Next to the script (development fallback)
    local = SCRIPT_DIR / "Tests"
    if local.exists():
        return local
    # 3. Glob search across iCloud (slow fallback)
    found = _find_dir_in_icloud("Tests")
    if found:
        return found
    return None


def find_formation_dir():
    # 1. Exact known iCloud path
    exact = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor"
    if exact.exists():
        return exact
    found = _find_dir_in_icloud("Formation Solicitor")
    if found:
        return found
    return SCRIPT_DIR


TESTS_DIR      = find_tests_dir()
FORMATION_DIR  = find_formation_dir()
PROGRESS_JSON  = SCRIPT_DIR / "progress.json"
LOG_FILE       = FORMATION_DIR / "server.log"
MOCK_EXAM_HTML = SCRIPT_DIR / "SQE1_MockExam.html"
GUIDE_HTML     = SCRIPT_DIR / "SQE1_HighYield_Standalone.html"

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("sqe1")

# ── Import parser from same folder ──────────────────────────────────────
sys.path.insert(0, str(SCRIPT_DIR))
import parse_questions  # noqa: E402

# ── Question cache (avoid re-parsing if PDFs haven't changed) ────────────
_q_cache: dict = {"sig": None, "data": None}


def _tests_signature():
    """MD5 of all PDF mtimes — changes whenever any PDF is added/modified."""
    if not TESTS_DIR or not TESTS_DIR.exists():
        return None
    pdfs = sorted(TESTS_DIR.glob("*.pdf"))
    h = hashlib.md5()
    for p in pdfs:
        h.update(f"{p.name}:{p.stat().st_mtime}".encode())
    return h.hexdigest()


def get_questions():
    sig = _tests_signature()
    if sig and sig == _q_cache["sig"]:
        return _q_cache["data"]
    questions = parse_questions.parse_all(str(TESTS_DIR))
    _q_cache["sig"]  = sig
    _q_cache["data"] = questions
    log.info(f"Parsed {len(questions)} questions (cache refreshed)")
    return questions


# ── Offline fallback page ────────────────────────────────────────────────
OFFLINE_HTML = b"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>SQE1 Server Offline</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f5f5f5;
     display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#fff;border-radius:12px;padding:40px 48px;text-align:center;
     box-shadow:0 2px 20px rgba(0,0,0,.12);max-width:480px}
h1{font-size:1.4rem;color:#b45309;margin-bottom:12px}
p{color:#555;line-height:1.6}
</style></head>
<body><div class="box">
<h1>&#9888; SQE1 Server Not Running</h1>
<p>The local SQE1 server is not running.<br>
Please open Cowork to restart it.</p>
</div></body></html>"""


# ── HTTP Handler ─────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # suppress default per-request output
        pass

    # ── helpers ──────────────────────────────────────────────────────────

    def _send(self, status, content_type, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def _html_file(self, path: Path):
        try:
            body = path.read_bytes()
            self._send(200, "text/html; charset=utf-8", body)
        except FileNotFoundError:
            self._send(404, "text/plain; charset=utf-8", b"File not found")
        except Exception as e:
            log.error(f"Serving {path}: {e}")
            self._send(500, "text/plain; charset=utf-8", str(e).encode())

    # ── OPTIONS (preflight, not really needed for same-origin) ───────────

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ── GET ──────────────────────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        log.info(f"GET {path}")

        if path in ("/", "/test"):
            self._html_file(MOCK_EXAM_HTML)

        elif path == "/guide":
            self._html_file(GUIDE_HTML)

        elif path == "/api/questions":
            if not TESTS_DIR or not TESTS_DIR.exists():
                self._json({"error": f"Tests folder not found (looked for: {TESTS_DIR})"}, 404)
                return
            try:
                t0 = time.time()
                questions = get_questions()
                log.info(f"  → {len(questions)} questions in {time.time()-t0:.2f}s")
                self._json(questions)
            except Exception as e:
                log.error(f"parse_all: {e}")
                self._json({"error": str(e)}, 500)

        elif path == "/api/progress":
            try:
                data = json.loads(PROGRESS_JSON.read_text("utf-8")) if PROGRESS_JSON.exists() else []
                self._json(data)
            except Exception as e:
                log.error(f"Read progress: {e}")
                self._json({"error": str(e)}, 500)

        else:
            self._send(404, "text/plain; charset=utf-8", b"Not found")

    # ── POST ─────────────────────────────────────────────────────────────

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        log.info(f"POST {path}")

        if path == "/api/progress":
            try:
                length  = int(self.headers.get("Content-Length", 0))
                body    = self.rfile.read(length)
                result  = json.loads(body.decode("utf-8"))

                existing = (
                    json.loads(PROGRESS_JSON.read_text("utf-8"))
                    if PROGRESS_JSON.exists() else []
                )
                existing.append(result)
                PROGRESS_JSON.write_text(
                    json.dumps(existing, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                paper = result.get("paper", "?")
                pct   = result.get("percentage", "?")
                log.info(f"  → saved {paper} {pct}%  (total sessions: {len(existing)})")
                self._json({"ok": True, "total_sessions": len(existing)})
            except Exception as e:
                log.error(f"Save progress: {e}")
                self._json({"error": str(e)}, 500)

        elif path == "/api/progress/delete":
            # Remove a session by its datetime key
            try:
                length   = int(self.headers.get("Content-Length", 0))
                body     = self.rfile.read(length)
                payload  = json.loads(body.decode("utf-8"))
                dt_key   = payload.get("datetime", "")
                existing = (
                    json.loads(PROGRESS_JSON.read_text("utf-8"))
                    if PROGRESS_JSON.exists() else []
                )
                before = len(existing)
                existing = [s for s in existing if s.get("datetime") != dt_key]
                PROGRESS_JSON.write_text(
                    json.dumps(existing, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                removed = before - len(existing)
                log.info(f"  → deleted {removed} session(s) matching {dt_key!r}")
                self._json({"ok": True, "removed": removed, "remaining": len(existing)})
            except Exception as e:
                log.error(f"Delete progress: {e}")
                self._json({"error": str(e)}, 500)

        elif path == "/api/annotate":
            # Proxy to Anthropic Claude API for annotation matching
            try:
                length   = int(self.headers.get("Content-Length", 0))
                body     = self.rfile.read(length)
                payload  = json.loads(body.decode("utf-8"))

                api_key  = payload.get("apiKey", "").strip()
                if not api_key:
                    self._json({"error": "apiKey missing"}, 400)
                    return

                q_text   = payload.get("questionText", "")
                u_ans    = payload.get("userAnswer", "(not recorded)")
                c_ans    = payload.get("correctAnswer", "")
                ch_text  = payload.get("chapterContent", "")

                prompt = (
                    "You are helping annotate a legal revision guide for the SQE1 bar exam.\n\n"
                    "A student answered the following exam question INCORRECTLY:\n\n"
                    f"QUESTION:\n{q_text}\n\n"
                    f"STUDENT'S WRONG ANSWER: {u_ans}\n"
                    f"CORRECT ANSWER: {c_ans}\n\n"
                    "Here is the revision guide content for the relevant chapter:\n"
                    f"{ch_text}\n\n"
                    "Identify the SINGLE content item from the revision guide that most directly "
                    "explains why the correct answer is right, or contains the key rule/nuance "
                    "the student is likely missing.\n\n"
                    'Return ONLY valid JSON (no other text): {"excerpt": "the exact first 65 characters of the matching item\'s text"}\n'
                    'If no item clearly matches, return: {"excerpt": null}'
                )

                anthropic_payload = json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 120,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=anthropic_payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))

                raw_text = resp_data["content"][0]["text"].strip()
                # Extract JSON even if Claude wraps it in markdown
                import re as _re
                m = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
                result_json = json.loads(m.group()) if m else {"excerpt": None}
                log.info(f"  → annotate: {result_json.get('excerpt','null')!r:.60}")
                self._json(result_json)

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                log.error(f"Anthropic API error {e.code}: {err_body[:200]}")
                self._json({"error": f"Anthropic {e.code}: {err_body[:200]}"}, 502)
            except Exception as e:
                log.error(f"Annotate: {e}")
                self._json({"error": str(e)}, 500)

        else:
            self._send(404, "text/plain; charset=utf-8", b"Not found")


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 60)
    log.info(f"SQE1 server  →  http://{HOST}:{PORT}")
    log.info(f"Tests dir    :  {TESTS_DIR or 'NOT FOUND'}")
    log.info(f"Progress     :  {PROGRESS_JSON}")
    log.info(f"Log file     :  {LOG_FILE}")
    log.info(f"Mock exam    :  {MOCK_EXAM_HTML}")
    log.info(f"Guide        :  {GUIDE_HTML}")
    log.info("=" * 60)

    if not TESTS_DIR or not TESTS_DIR.exists():
        log.warning("Tests folder not found — /api/questions will return 404")

    if not GUIDE_HTML.exists():
        log.warning(f"Guide HTML not found: {GUIDE_HTML} — /guide will return 404")

    if not MOCK_EXAM_HTML.exists():
        log.warning(f"Mock exam HTML not found: {MOCK_EXAM_HTML} — / and /test will return 404")

    server = HTTPServer((HOST, PORT), Handler)
    log.info("Ready. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
