#!/usr/bin/env python3
"""
SQE1 Mock Exam Builder
Runs parse_questions.py, embeds the question bank into the HTML template,
and writes SQE1_MockExam.html to the output directory.
"""
import json, os, subprocess, sys, webbrowser
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
PARSER      = SCRIPT_DIR / "parse_questions.py"
OUTPUT_HTML = SCRIPT_DIR / "SQE1_MockExam.html"

# ── Accept tests dir as first argument, otherwise look next to script ──────────
if len(sys.argv) > 1:
    TESTS_DIR = sys.argv[1]
else:
    TESTS_DIR = str(SCRIPT_DIR / "Tests")

print(f"Parsing PDFs from: {TESTS_DIR}")
result = subprocess.run(
    [sys.executable, str(PARSER), TESTS_DIR],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("Parser failed:", result.stderr); sys.exit(1)

try:
    questions = json.loads(result.stdout)
except json.JSONDecodeError as e:
    print("Could not parse JSON:", e)
    print("Parser stderr:", result.stderr[:500])
    sys.exit(1)

print(result.stderr.rstrip())

# Escape the JSON for safe embedding inside a <script> tag
qbank_js = json.dumps(questions, ensure_ascii=False)
# Prevent </script> in strings from breaking the page
qbank_js = qbank_js.replace("</script>", "<\\/script>")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SQE1 Mock Exam</title>
<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, Arial, sans-serif; font-size: 16px;
       background: #f5f5f5; color: #1a1a1a; min-height: 100vh; }
button { cursor: pointer; font-family: inherit; }

/* ── Screens ── */
.screen { display: none; }
.screen.active { display: block; }

/* ════════════════════════════════════════════
   SETUP SCREEN
════════════════════════════════════════════ */
#screen-setup {
  max-width: 680px; margin: 48px auto; padding: 0 16px 48px;
}
.setup-header { text-align: center; margin-bottom: 36px; }
.setup-header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 6px; }
.setup-header p  { color: #555; font-size: 0.95rem; }
.setup-card {
  background: #fff; border: 1px solid #ddd; border-radius: 10px;
  padding: 28px 32px; margin-bottom: 20px;
}
.setup-card h2 { font-size: 1rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: .06em; color: #444; margin-bottom: 18px; }
.radio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.radio-grid.cols4 { grid-template-columns: repeat(4,1fr); }
.radio-option { position: relative; }
.radio-option input { position: absolute; opacity: 0; width: 0; height: 0; }
.radio-option label {
  display: block; padding: 14px 16px; border: 2px solid #ddd;
  border-radius: 8px; cursor: pointer; transition: all .15s;
  text-align: center; font-weight: 500;
}
.radio-option input:checked + label {
  border-color: #1a56db; background: #eff6ff; color: #1a56db;
}
.radio-option label:hover { border-color: #999; }
.radio-option .sub { font-size: 0.78rem; font-weight: 400; color: #777; margin-top: 2px; }
#bank-summary { font-size: 0.88rem; color: #444; line-height: 1.7; }
#bank-summary .subject-row { display: flex; justify-content: space-between; }
#bank-summary .warn { color: #b45309; font-weight: 500; }
#coverage-banner {
  background: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px;
  padding: 12px 16px; font-size: 0.88rem; color: #92400e; margin-bottom: 20px;
  display: none;
}

/* ── Progress Dashboard (setup screen) ── */
#dashboard-card {
  background: #fff; border: 1px solid #ddd; border-radius: 10px;
  padding: 22px 28px; margin-bottom: 20px;
}
#dashboard-card h2 { font-size: 1rem; font-weight: 600; text-transform: uppercase;
                     letter-spacing: .06em; color: #444; margin-bottom: 14px; }
#dash-loading { color: #999; font-size: 0.88rem; }
#dash-empty   { color: #999; font-size: 0.88rem; }
.dash-stats { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.dash-stat  { text-align: center; }
.dash-stat .val { font-size: 1.5rem; font-weight: 700; color: #1a56db; }
.dash-stat .lbl { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: .04em; }
.dash-hist  { display: flex; flex-direction: column; gap: 6px; }
.dash-row   { display: flex; align-items: center; gap: 10px; font-size: 0.82rem; }
.dash-date  { color: #888; min-width: 130px; }
.dash-paper { font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; }
.dash-paper.FLK1 { background: #ede9fe; color: #5b21b6; }
.dash-paper.FLK2 { background: #e0f2fe; color: #0369a1; }
.dash-bar-wrap { flex: 1; height: 7px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.dash-bar-fill { height: 100%; border-radius: 4px; background: #1a56db; }
.dash-bar-fill.low { background: #f59e0b; }
.dash-pct { font-weight: 600; min-width: 38px; text-align: right; }
.dash-pct.pass { color: #16a34a; }
.dash-pct.fail { color: #dc2626; }
#btn-start {
  width: 100%; padding: 16px; font-size: 1.1rem; font-weight: 600;
  background: #1a56db; color: #fff; border: none; border-radius: 8px;
  transition: background .15s;
}
#btn-start:hover { background: #1649c0; }
#btn-start:disabled { background: #9eb8ef; cursor: default; }

/* ════════════════════════════════════════════
   EXAM SCREEN
════════════════════════════════════════════ */
#screen-exam { height: 100vh; display: none; flex-direction: column; }
#screen-exam.active { display: flex; }
#exam-topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #ddd; padding: 10px 20px;
  flex-shrink: 0; gap: 16px; flex-wrap: wrap;
}
#exam-title { font-size: 0.9rem; font-weight: 600; color: #333; }
#exam-progress { font-size: 0.85rem; color: #555; }
#timer-wrap { display: flex; align-items: center; gap: 8px; }
#timer-label { font-size: 0.8rem; color: #888; }
#timer {
  font-size: 1.25rem; font-weight: 700; color: #1a56db;
  font-variant-numeric: tabular-nums; min-width: 68px; text-align: right;
}
#timer.warn { color: #dc2626; }
.exam-actions { display: flex; gap: 8px; }
#btn-flag {
  padding: 7px 14px; font-size: 0.82rem; border: 1.5px solid #d97706;
  color: #d97706; background: #fff; border-radius: 6px; font-weight: 500;
}
#btn-flag.flagged { background: #fffbeb; }
#btn-calc {
  padding: 7px 14px; font-size: 0.82rem; border: 1.5px solid #6b7280;
  color: #6b7280; background: #fff; border-radius: 6px; font-weight: 500;
}
#btn-end {
  padding: 7px 14px; font-size: 0.82rem; border: 1.5px solid #dc2626;
  color: #dc2626; background: #fff; border-radius: 6px; font-weight: 500;
}

/* Exam body layout */
#exam-body { display: flex; flex: 1; overflow: hidden; }

/* Navigator panel */
#nav-panel {
  width: 220px; background: #fff; border-right: 1px solid #ddd;
  overflow-y: auto; flex-shrink: 0; padding: 16px;
}
#nav-panel h3 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: .06em;
                color: #888; margin-bottom: 12px; }
#nav-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 5px; }
.nav-btn {
  aspect-ratio: 1; font-size: 0.72rem; font-weight: 600;
  border: 1.5px solid #ddd; border-radius: 4px; background: #fff;
  color: #555; cursor: pointer; display: flex; align-items: center;
  justify-content: center;
}
.nav-btn.answered { background: #dbeafe; border-color: #93c5fd; color: #1e40af; }
.nav-btn.flagged  { background: #fef3c7; border-color: #fcd34d; color: #92400e; }
.nav-btn.answered.flagged { background: #fef3c7; border-color: #f59e0b; }
.nav-btn.current  { border-color: #1a56db; box-shadow: 0 0 0 2px #1a56db; }
#nav-legend { margin-top: 14px; font-size: 0.75rem; color: #666; line-height: 1.9; }
.legend-dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 2px; margin-right: 5px; vertical-align: middle;
}

/* Question area */
#question-area {
  flex: 1; overflow-y: auto; padding: 28px 36px;
  display: flex; flex-direction: column; gap: 24px;
}
#question-number { font-size: 0.82rem; color: #888; font-weight: 500; }
#question-subject { font-size: 0.78rem; color: #6b7280; }
#question-text {
  font-size: 1.02rem; line-height: 1.75; color: #111;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px;
}
#options-form { display: flex; flex-direction: column; gap: 10px; }
.option-label {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px 18px; border: 2px solid #e5e7eb; border-radius: 8px;
  cursor: pointer; background: #fff; transition: all .12s;
}
.option-label:hover { border-color: #93c5fd; background: #f8fafc; }
.option-label.selected { border-color: #1a56db; background: #eff6ff; }
.option-label input { display: none; }
.option-letter {
  font-weight: 700; font-size: 0.95rem; color: #1a56db;
  min-width: 22px; padding-top: 1px;
}
.option-text { font-size: 0.97rem; line-height: 1.6; }
#btn-confirm {
  align-self: flex-start; padding: 12px 32px; font-size: 1rem; font-weight: 600;
  background: #1a56db; color: #fff; border: none; border-radius: 8px;
  transition: background .15s;
}
#btn-confirm:hover { background: #1649c0; }
#btn-confirm:disabled { background: #9eb8ef; cursor: default; }
#confirm-hint { font-size: 0.83rem; color: #888; align-self: flex-start; }

/* ── Calculator ── */
#calculator {
  position: fixed; bottom: 80px; right: 24px; width: 220px;
  background: #1f2937; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,.3);
  padding: 14px; display: none; z-index: 1000; user-select: none;
}
#calculator.visible { display: block; }
#calc-display {
  background: #374151; color: #f9fafb; font-size: 1.4rem; text-align: right;
  padding: 10px 12px; border-radius: 6px; margin-bottom: 10px;
  font-variant-numeric: tabular-nums; word-break: break-all; min-height: 52px;
}
.calc-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 6px; }
.calc-btn {
  padding: 12px 6px; font-size: 0.9rem; font-weight: 600;
  border: none; border-radius: 6px; color: #f9fafb; cursor: pointer;
  transition: filter .1s;
}
.calc-btn:hover { filter: brightness(1.15); }
.calc-btn.num  { background: #4b5563; }
.calc-btn.op   { background: #1a56db; }
.calc-btn.eq   { background: #16a34a; grid-column: span 2; }
.calc-btn.clr  { background: #dc2626; }
.calc-btn.back { background: #6b7280; }
#calc-drag-bar {
  text-align: center; color: #9ca3af; font-size: 0.72rem;
  margin-bottom: 8px; cursor: grab;
}

/* ── Modal overlay ── */
#modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 2000;
  display: none;
}
#modal-overlay.visible { display: flex; }
#modal-box {
  background: #fff; border-radius: 12px; padding: 32px 36px; max-width: 420px;
  width: 90%; text-align: center;
}
#modal-box h2 { margin-bottom: 12px; font-size: 1.2rem; }
#modal-box p  { color: #555; margin-bottom: 24px; font-size: 0.95rem; line-height: 1.6; }
#modal-actions { display: flex; gap: 12px; justify-content: center; }
#modal-cancel {
  padding: 10px 24px; border: 1.5px solid #ddd; border-radius: 7px;
  background: #fff; color: #333; font-weight: 500; font-size: 0.95rem;
}
#modal-confirm {
  padding: 10px 24px; background: #dc2626; color: #fff; border: none;
  border-radius: 7px; font-weight: 600; font-size: 0.95rem;
}

/* ════════════════════════════════════════════
   RESULTS SCREEN
════════════════════════════════════════════ */
#screen-results { max-width: 860px; margin: 0 auto; padding: 32px 16px 64px; }
.results-header { text-align: center; margin-bottom: 32px; }
.results-header h1 { font-size: 1.8rem; margin-bottom: 6px; }
.score-circle {
  display: inline-flex; align-items: center; justify-content: center;
  width: 120px; height: 120px; border-radius: 50%; margin: 20px auto;
  font-size: 2rem; font-weight: 700; border: 6px solid;
}
.score-circle.pass { border-color: #16a34a; color: #16a34a; background: #f0fdf4; }
.score-circle.fail { border-color: #dc2626; color: #dc2626; background: #fef2f2; }
.results-card {
  background: #fff; border: 1px solid #ddd; border-radius: 10px;
  padding: 24px 28px; margin-bottom: 20px;
}
.results-card h2 { font-size: 0.95rem; font-weight: 600; text-transform: uppercase;
                   letter-spacing: .06em; color: #555; margin-bottom: 18px; }
.subj-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.subj-table th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #e5e7eb;
                 color: #555; font-weight: 600; }
.subj-table td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; }
.subj-table tr:last-child td { border-bottom: none; }
.subj-bar { height: 8px; border-radius: 4px; background: #e5e7eb; overflow: hidden; }
.subj-bar-fill { height: 100%; border-radius: 4px; background: #1a56db; }
.subj-bar-fill.low { background: #f59e0b; }
.pct-badge {
  display: inline-block; padding: 2px 8px; border-radius: 20px;
  font-size: 0.8rem; font-weight: 600;
}
.pct-badge.ok  { background: #d1fae5; color: #065f46; }
.pct-badge.low { background: #fef3c7; color: #92400e; }
.review-section { margin-bottom: 12px; }
.review-q {
  border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 10px;
  overflow: hidden;
}
.review-q-header {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px;
  cursor: pointer; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
  font-size: 0.88rem;
}
.review-q-header .q-status {
  width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
  font-size: 0.72rem; display: flex; align-items: center; justify-content: center;
  font-weight: 700; color: #fff;
}
.q-status.correct { background: #16a34a; }
.q-status.wrong   { background: #dc2626; }
.q-status.skipped { background: #9ca3af; }
.review-q-body { padding: 16px; display: none; }
.review-q-body.open { display: block; }
.review-q-body .q-text { font-size: 0.92rem; line-height: 1.7; margin-bottom: 14px; }
.review-option {
  padding: 10px 14px; border-radius: 6px; font-size: 0.88rem;
  margin-bottom: 6px; line-height: 1.5;
  display: flex; align-items: flex-start; gap: 10px;
}
.review-option .ol { font-weight: 700; min-width: 18px; }
.review-option.correct-ans  { background: #d1fae5; color: #065f46; }
.review-option.user-wrong   { background: #fee2e2; color: #991b1b; }
.review-option.neutral      { color: #555; }
.review-q-header .q-num { font-weight: 600; color: #333; min-width: 28px; }
.review-q-header .q-snippet { color: #666; flex: 1; white-space: nowrap;
                               overflow: hidden; text-overflow: ellipsis; }
.review-q-header .q-subj { font-size: 0.78rem; color: #999; flex-shrink: 0; }

#btn-print {
  padding: 12px 28px; font-size: 1rem; font-weight: 600;
  background: #1a56db; color: #fff; border: none; border-radius: 8px;
  margin-right: 10px;
}
#btn-new-session {
  padding: 12px 28px; font-size: 1rem; font-weight: 600;
  background: #fff; color: #1a56db; border: 2px solid #1a56db; border-radius: 8px;
}

/* ── Print styles ── */
@media print {
  #btn-print, #btn-new-session, .review-q-header { background: none !important; }
  .review-q-body { display: block !important; }
  .screen.active { display: block !important; }
  #screen-setup, #screen-exam { display: none !important; }
  #screen-results { display: block !important; max-width: 100%; }
  body { background: #fff; }
}
@media (max-width: 600px) {
  #nav-panel { display: none; }
  #question-area { padding: 16px; }
  .radio-grid.cols4 { grid-template-columns: 1fr 1fr; }
}
</style>
</head>
<body>

<!-- ══════════ SETUP SCREEN ══════════ -->
<div id="screen-setup" class="screen active">
  <div class="setup-header">
    <h1>SQE1 Mock Exam</h1>
    <p>Exam-condition practice · Questions drawn exclusively from your question bank</p>
  </div>

  <div class="setup-card">
    <h2>Select Paper</h2>
    <div class="radio-grid">
      <div class="radio-option">
        <input type="radio" name="paper" id="p-flk1" value="FLK1" checked>
        <label for="p-flk1">FLK1
          <div class="sub">Business · Dispute · Contract · Tort · Legal Services · Legal System</div>
        </label>
      </div>
      <div class="radio-option">
        <input type="radio" name="paper" id="p-flk2" value="FLK2">
        <label for="p-flk2">FLK2
          <div class="sub">Property · Wills · Land · Criminal · Trusts · Solicitors Accounts</div>
        </label>
      </div>
    </div>
  </div>

  <div class="setup-card">
    <h2>Session Duration</h2>
    <div class="radio-grid cols4">
      <div class="radio-option">
        <input type="radio" name="duration" id="d-30" value="30" checked>
        <label for="d-30">30 min<div class="sub">~18 questions</div></label>
      </div>
      <div class="radio-option">
        <input type="radio" name="duration" id="d-60" value="60">
        <label for="d-60">60 min<div class="sub">~35 questions</div></label>
      </div>
      <div class="radio-option">
        <input type="radio" name="duration" id="d-90" value="90">
        <label for="d-90">90 min<div class="sub">~53 questions</div></label>
      </div>
      <div class="radio-option">
        <input type="radio" name="duration" id="d-full" value="153">
        <label for="d-full">Full<div class="sub">90 q · 153 min</div></label>
      </div>
    </div>
  </div>

  <div class="setup-card">
    <h2>Question Bank — Available Questions</h2>
    <div id="bank-summary">Select a paper above to see coverage.</div>
  </div>

  <div class="setup-card" id="dashboard-card">
    <h2>Your Progress</h2>
    <div id="dash-loading">Loading scores…</div>
    <div id="dash-content" style="display:none"></div>
  </div>

  <div id="coverage-banner"></div>
  <button id="btn-start">Begin Session</button>
</div>

<!-- ══════════ EXAM SCREEN ══════════ -->
<div id="screen-exam" class="screen">
  <div id="exam-topbar">
    <div>
      <div id="exam-title">SQE1 Mock Exam</div>
      <div id="exam-progress"></div>
    </div>
    <div id="timer-wrap">
      <span id="timer-label">Time remaining</span>
      <span id="timer">00:00</span>
    </div>
    <div class="exam-actions">
      <button id="btn-flag">⚑ Flag</button>
      <button id="btn-calc">⊞ Calculator</button>
      <button id="btn-end">End Session</button>
    </div>
  </div>

  <div id="exam-body">
    <div id="nav-panel">
      <h3>Questions</h3>
      <div id="nav-grid"></div>
      <div id="nav-legend">
        <div><span class="legend-dot" style="background:#dbeafe;border:1px solid #93c5fd"></span>Answered</div>
        <div><span class="legend-dot" style="background:#fef3c7;border:1px solid #fcd34d"></span>Flagged</div>
        <div><span class="legend-dot" style="background:#fff;border:1px solid #ddd"></span>Unanswered</div>
      </div>
    </div>

    <div id="question-area">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span id="question-number"></span>
        <span id="question-subject"></span>
      </div>
      <div id="question-text"></div>
      <form id="options-form" onsubmit="return false;"></form>
      <button id="btn-confirm" disabled>Confirm Answer →</button>
      <p id="confirm-hint">Select an answer to continue. Answers cannot be changed after confirming.</p>
    </div>
  </div>
</div>

<!-- ══════════ RESULTS SCREEN ══════════ -->
<div id="screen-results" class="screen">
  <div class="results-header">
    <h1>Session Complete</h1>
    <div id="score-circle-wrap"></div>
    <p id="score-summary"></p>
    <p style="font-size:0.82rem;color:#888;margin-top:6px">
      Reference pass mark: 60% — SRA pass mark varies by sitting; 60% used here as a guide.
    </p>
  </div>

  <div class="results-card">
    <h2>Score by Subject</h2>
    <table class="subj-table">
      <thead><tr>
        <th>Subject</th><th>Score</th><th>%</th><th style="width:140px">Progress</th>
      </tr></thead>
      <tbody id="subj-table-body"></tbody>
    </table>
  </div>

  <div class="results-card">
    <h2>Question Review</h2>
    <div id="review-list"></div>
  </div>

  <div style="text-align:center;margin-top:24px">
    <button id="btn-print">Export / Print Results</button>
    <button id="btn-new-session">New Session</button>
  </div>
</div>

<!-- ══════════ CALCULATOR ══════════ -->
<div id="calculator">
  <div id="calc-drag-bar">⠿ Calculator</div>
  <div id="calc-display">0</div>
  <div class="calc-grid">
    <button class="calc-btn clr"  onclick="calcAction('C')">C</button>
    <button class="calc-btn back" onclick="calcAction('⌫')">⌫</button>
    <button class="calc-btn op"   onclick="calcAction('%')">%</button>
    <button class="calc-btn op"   onclick="calcAction('/')">÷</button>
    <button class="calc-btn num"  onclick="calcAction('7')">7</button>
    <button class="calc-btn num"  onclick="calcAction('8')">8</button>
    <button class="calc-btn num"  onclick="calcAction('9')">9</button>
    <button class="calc-btn op"   onclick="calcAction('*')">×</button>
    <button class="calc-btn num"  onclick="calcAction('4')">4</button>
    <button class="calc-btn num"  onclick="calcAction('5')">5</button>
    <button class="calc-btn num"  onclick="calcAction('6')">6</button>
    <button class="calc-btn op"   onclick="calcAction('-')">−</button>
    <button class="calc-btn num"  onclick="calcAction('1')">1</button>
    <button class="calc-btn num"  onclick="calcAction('2')">2</button>
    <button class="calc-btn num"  onclick="calcAction('3')">3</button>
    <button class="calc-btn op"   onclick="calcAction('+')">+</button>
    <button class="calc-btn num"  onclick="calcAction('0')" style="grid-column:span 2">0</button>
    <button class="calc-btn num"  onclick="calcAction('.')">.</button>
    <button class="calc-btn eq"   onclick="calcAction('=')">=</button>
  </div>
</div>

<!-- ══════════ MODAL ══════════ -->
<div id="modal-overlay">
  <div id="modal-box">
    <h2 id="modal-title">End Session?</h2>
    <p id="modal-body">You have unanswered questions. Are you sure you want to submit?</p>
    <div id="modal-actions">
      <button id="modal-cancel" onclick="closeModal()">Continue Exam</button>
      <button id="modal-confirm" onclick="submitExam()">Submit</button>
    </div>
  </div>
</div>

<script>
// ══════════════════════════════════════════════════════════
//  QUESTION BANK (embedded by build_exam.py)
// ══════════════════════════════════════════════════════════
const QUESTION_BANK = """ + qbank_js + r""";

// ══════════════════════════════════════════════════════════
//  PROGRESS API (Hostinger)
// ══════════════════════════════════════════════════════════
const PROGRESS_API = 'https://bidouillecode.dev/solicitor/progress.php';

async function fetchSessions() {
  try {
    const r = await fetch(PROGRESS_API);
    if (r.ok) return await r.json();
  } catch(e) {}
  return [];
}

async function saveSession(data) {
  try {
    await fetch(PROGRESS_API, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
  } catch(e) { console.warn('Could not save session to server:', e); }
}

function renderDashboard(sessions) {
  const loading = document.getElementById('dash-loading');
  const content = document.getElementById('dash-content');
  loading.style.display = 'none';
  content.style.display = 'block';

  if (!sessions || sessions.length === 0) {
    content.innerHTML = '<div id="dash-empty">No sessions yet — complete your first exam to see scores here.</div>';
    return;
  }

  const sorted = [...sessions].sort((a,b) => new Date(b.datetime) - new Date(a.datetime));
  const avg  = Math.round(sorted.reduce((s,x) => s + x.percentage, 0) / sorted.length);
  const best = Math.max(...sorted.map(x => x.percentage));
  const last = sorted[0];
  const trend = sorted.length >= 2 ? sorted[0].percentage - sorted[1].percentage : null;
  const trendStr = trend === null ? '' : (trend >= 0 ? ` ▲${trend}%` : ` ▼${Math.abs(trend)}%`);
  const trendCol = trend === null ? '' : trend >= 0 ? 'color:#16a34a' : 'color:#dc2626';

  const rows = sorted.slice(0,6).map(s => {
    const d   = new Date(s.datetime);
    const lbl = d.toLocaleDateString('en-GB',{day:'numeric',month:'short'}) + ' ' +
                d.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
    const pass = s.percentage >= 60;
    return `<div class="dash-row">
      <span class="dash-date">${lbl}</span>
      <span class="dash-paper ${s.paper}">${s.paper}</span>
      <div class="dash-bar-wrap"><div class="dash-bar-fill ${pass?'':'low'}" style="width:${s.percentage}%"></div></div>
      <span class="dash-pct ${pass?'pass':'fail'}">${s.percentage}%</span>
    </div>`;
  }).join('');

  content.innerHTML = `
    <div class="dash-stats">
      <div class="dash-stat"><div class="val">${sorted.length}</div><div class="lbl">Sessions</div></div>
      <div class="dash-stat"><div class="val">${avg}%<span style="font-size:0.9rem;${trendCol}">${trendStr}</span></div><div class="lbl">Average</div></div>
      <div class="dash-stat"><div class="val">${best}%</div><div class="lbl">Best</div></div>
    </div>
    <div class="dash-hist">${rows}</div>`;
}

// Load dashboard on page start
fetchSessions().then(renderDashboard);

// ══════════════════════════════════════════════════════════
//  CONFIGURATION
// ══════════════════════════════════════════════════════════
const PAPER_SUBJECTS = {
  FLK1: {
    "Business Law and Practice":          20,
    "Dispute Resolution":                  20,
    "Contract Law":                        18,
    "Tort":                                16,
    "Legal Services":                      14,
    "Legal System":                        12,
    "Ethics and Professional Conduct":     15,
  },
  FLK2: {
    "Property Law and Practice":           20,
    "Wills and Administration of Estates": 18,
    "Land Law":                            16,
    "Criminal Law and Practice":           16,
    "Trusts Law":                          14,
    "Solicitors Accounts":                  8,
    "Criminal Liability":                   8,
    "Ethics and Professional Conduct":     15,
  }
};

const DURATION_TO_QS = { "30": 18, "60": 35, "90": 53, "153": 90 };
const LETTERS = ["A","B","C","D","E"];

// ══════════════════════════════════════════════════════════
//  STATE
// ══════════════════════════════════════════════════════════
let session = {
  paper: "FLK1",
  totalMinutes: 30,
  questions: [],      // [{...q, shuffledOptions, correctShuffledIdx}]
  answers: [],        // index into shuffledOptions, or null
  flags: [],
  currentIdx: 0,
  timerInterval: null,
  secondsLeft: 0,
  submitted: false,
};

// ══════════════════════════════════════════════════════════
//  SETUP SCREEN
// ══════════════════════════════════════════════════════════
function buildBankSummary() {
  const paper = document.querySelector('input[name="paper"]:checked').value;
  const dur   = document.querySelector('input[name="duration"]:checked').value;
  const totalQ = DURATION_TO_QS[dur];
  const weights = PAPER_SUBJECTS[paper];

  // Pool: paper-specific + BOTH (ethics)
  const pool = QUESTION_BANK.filter(q => q.paper === paper || q.paper === "BOTH");

  // Count available per subject
  const available = {};
  for (const subj of Object.keys(weights)) available[subj] = 0;
  for (const q of pool) {
    if (weights[q.subject] !== undefined) available[q.subject] = (available[q.subject]||0) + 1;
  }

  // Compute targets
  const totalWeight = Object.values(weights).reduce((a,b)=>a+b,0);
  const targets = {};
  let targetSum = 0;
  const subjList = Object.keys(weights);
  subjList.forEach((s,i) => {
    const t = (i === subjList.length-1)
      ? totalQ - targetSum
      : Math.round(weights[s] / totalWeight * totalQ);
    targets[s] = t;
    targetSum += t;
  });

  let html = '';
  let hasGap = false;
  for (const subj of subjList) {
    const avail = available[subj] || 0;
    const tgt   = targets[subj];
    const warn  = avail < tgt;
    if (warn) hasGap = true;
    html += `<div class="subject-row ${warn?'warn':''}">
      <span>${subj}</span>
      <span>${avail} available · ${tgt} needed</span>
    </div>`;
  }
  document.getElementById('bank-summary').innerHTML = html;

  const banner = document.getElementById('coverage-banner');
  if (hasGap) {
    banner.style.display = 'block';
    banner.textContent = `⚠ Your question bank currently has ${pool.length} questions available for this paper. Some subjects are under-represented. Add more PDFs to the Tests folder and re-run the generator to improve coverage.`;
  } else {
    banner.style.display = 'none';
  }
}

document.querySelectorAll('input[name="paper"], input[name="duration"]')
  .forEach(el => el.addEventListener('change', buildBankSummary));
buildBankSummary();

document.getElementById('btn-start').addEventListener('click', () => {
  const paper    = document.querySelector('input[name="paper"]:checked').value;
  const durStr   = document.querySelector('input[name="duration"]:checked').value;
  startSession(paper, parseInt(durStr));
});

// ══════════════════════════════════════════════════════════
//  SESSION SETUP
// ══════════════════════════════════════════════════════════
function shuffle(arr) {
  for (let i = arr.length-1; i > 0; i--) {
    const j = Math.floor(Math.random()*(i+1));
    [arr[i],arr[j]] = [arr[j],arr[i]];
  }
  return arr;
}

function selectQuestions(paper, totalQ) {
  const weights  = PAPER_SUBJECTS[paper];
  const pool     = QUESTION_BANK.filter(q => q.paper===paper || q.paper==="BOTH");

  // Bucket by subject
  const buckets = {};
  for (const subj of Object.keys(weights)) buckets[subj] = [];
  for (const q of pool) {
    if (buckets[q.subject] !== undefined) buckets[q.subject].push(q);
  }
  for (const subj of Object.keys(buckets)) shuffle(buckets[subj]);

  const totalWeight = Object.values(weights).reduce((a,b)=>a+b,0);
  const subjList    = Object.keys(weights);
  let selected = [];

  // First pass: take up to target from each subject
  const targets = {};
  let tSum = 0;
  subjList.forEach((s,i) => {
    const t = (i===subjList.length-1)
      ? totalQ - tSum
      : Math.round(weights[s]/totalWeight*totalQ);
    targets[s] = Math.min(t, buckets[s].length);
    tSum += targets[s];
  });

  for (const subj of subjList) {
    selected.push(...buckets[subj].slice(0, targets[subj]));
    buckets[subj] = buckets[subj].slice(targets[subj]);
  }

  // Fill shortfall from remaining questions
  if (selected.length < totalQ) {
    const extras = shuffle(Object.values(buckets).flat());
    selected.push(...extras.slice(0, totalQ - selected.length));
  }

  selected = shuffle(selected.slice(0, totalQ));

  // Attach shuffled options for each question
  return selected.map(q => {
    const idxMap = shuffle([0,1,2,3,4]);
    const shuffledOptions = idxMap.map(i => q.options[i]);
    const correctShuffledIdx = idxMap.indexOf(q.correct_index);
    return { ...q, shuffledOptions, correctShuffledIdx };
  });
}

function startSession(paper, durationMinutes) {
  const totalQ = DURATION_TO_QS[String(durationMinutes)] || 18;
  const qs     = selectQuestions(paper, totalQ);

  if (qs.length === 0) {
    alert("No questions available for this paper. Add PDFs to the Tests folder and regenerate the exam."); return;
  }

  session = {
    paper, totalMinutes: durationMinutes,
    questions: qs, answers: Array(qs.length).fill(null),
    flags: Array(qs.length).fill(false),
    currentIdx: 0, timerInterval: null,
    secondsLeft: durationMinutes * 60, submitted: false,
  };

  showScreen('exam');
  buildNavGrid();
  renderQuestion(0);
  startTimer();
}

// ══════════════════════════════════════════════════════════
//  EXAM SCREEN
// ══════════════════════════════════════════════════════════
function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-'+name).classList.add('active');
}

function buildNavGrid() {
  const grid = document.getElementById('nav-grid');
  grid.innerHTML = '';
  session.questions.forEach((_, i) => {
    const btn = document.createElement('button');
    btn.className = 'nav-btn';
    btn.textContent = i+1;
    btn.onclick = () => jumpTo(i);
    btn.id = `nav-${i}`;
    grid.appendChild(btn);
  });
}

function updateNav() {
  session.questions.forEach((_, i) => {
    const btn = document.getElementById(`nav-${i}`);
    if (!btn) return;
    btn.className = 'nav-btn' +
      (session.answers[i] !== null ? ' answered' : '') +
      (session.flags[i]            ? ' flagged'  : '') +
      (i === session.currentIdx    ? ' current'  : '');
  });
}

function renderQuestion(idx) {
  const q = session.questions[idx];
  session.currentIdx = idx;

  document.getElementById('exam-title').textContent = `SQE1 ${session.paper} Mock Exam`;
  document.getElementById('exam-progress').textContent =
    `Question ${idx+1} of ${session.questions.length}`;
  document.getElementById('question-number').textContent = `Question ${idx+1}`;
  document.getElementById('question-subject').textContent = q.subject;
  document.getElementById('question-text').textContent = q.question_text;

  // Build options
  const form = document.getElementById('options-form');
  form.innerHTML = '';
  q.shuffledOptions.forEach((opt, li) => {
    const label = document.createElement('label');
    label.className = 'option-label' + (session.answers[idx]===li ? ' selected' : '');
    label.innerHTML = `<input type="radio" name="opt" value="${li}">
      <span class="option-letter">${LETTERS[li]}</span>
      <span class="option-text">${escHtml(opt)}</span>`;
    label.querySelector('input').addEventListener('change', () => {
      document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
      label.classList.add('selected');
      document.getElementById('btn-confirm').disabled = false;
    });
    if (session.answers[idx] === li) label.querySelector('input').checked = true;
    form.appendChild(label);
  });

  // Flag button state
  const flagBtn = document.getElementById('btn-flag');
  flagBtn.classList.toggle('flagged', session.flags[idx]);
  flagBtn.textContent = session.flags[idx] ? '⚑ Flagged' : '⚑ Flag';

  // Confirm button
  const confirmBtn = document.getElementById('btn-confirm');
  confirmBtn.disabled = session.answers[idx] === null;
  confirmBtn.textContent = idx < session.questions.length-1 ? 'Confirm Answer →' : 'Confirm & Finish';

  updateNav();
}

function jumpTo(idx) {
  // Allow jumping only to answered questions or current ±1 (no back on confirmed)
  // Actually: can jump to any question that hasn't been answered yet, or view answered (read-only)
  session.currentIdx = idx;
  renderQuestion(idx);
}

// Confirm answer
document.getElementById('btn-confirm').addEventListener('click', () => {
  const checked = document.querySelector('input[name="opt"]:checked');
  if (!checked) return;
  session.answers[session.currentIdx] = parseInt(checked.value);
  updateNav();

  const next = session.currentIdx + 1;
  if (next < session.questions.length) {
    renderQuestion(next);
  } else {
    // All questions done or this was last
    const unanswered = session.answers.filter(a => a===null).length;
    if (unanswered === 0) {
      confirmSubmit();
    } else {
      renderQuestion(session.questions.findIndex((_,i) => session.answers[i]===null));
    }
  }
});

// Flag
document.getElementById('btn-flag').addEventListener('click', () => {
  const i = session.currentIdx;
  session.flags[i] = !session.flags[i];
  document.getElementById('btn-flag').classList.toggle('flagged', session.flags[i]);
  document.getElementById('btn-flag').textContent = session.flags[i] ? '⚑ Flagged' : '⚑ Flag';
  updateNav();
});

// End session
document.getElementById('btn-end').addEventListener('click', () => {
  const unanswered = session.answers.filter(a => a===null).length;
  const flagged    = session.flags.filter(Boolean).length;
  document.getElementById('modal-title').textContent = 'End Session?';
  document.getElementById('modal-body').textContent =
    `You have ${unanswered} unanswered and ${flagged} flagged question${flagged!==1?'s':''}. ` +
    `Submitting now will mark unanswered questions as incorrect. Are you sure?`;
  openModal();
});

function confirmSubmit() {
  document.getElementById('modal-title').textContent = 'Submit Session?';
  document.getElementById('modal-body').textContent =
    'All questions are answered. Ready to submit and see your results?';
  openModal();
}

function openModal()  { document.getElementById('modal-overlay').classList.add('visible'); }
function closeModal() { document.getElementById('modal-overlay').classList.remove('visible'); }

function submitExam() {
  closeModal();
  stopTimer();
  session.submitted = true;

  // Build result and save to Hostinger
  const qs = session.questions;
  let correct = 0;
  const subjMap = {};
  qs.forEach((q,i) => {
    if (!subjMap[q.subject]) subjMap[q.subject] = {correct:0, total:0};
    subjMap[q.subject].total++;
    if (session.answers[i] === q.correctShuffledIdx) { correct++; subjMap[q.subject].correct++; }
  });
  const result = {
    datetime:     new Date().toISOString(),
    paper:        session.paper,
    durationMode: String(session.totalMinutes),
    totalQ:       qs.length,
    correct:      correct,
    percentage:   Math.round(correct / qs.length * 100),
    subjects:     subjMap,
    questions:    []
  };
  saveSession(result);

  showResults();
}

// ══════════════════════════════════════════════════════════
//  TIMER
// ══════════════════════════════════════════════════════════
function startTimer() {
  updateTimerDisplay();
  session.timerInterval = setInterval(() => {
    session.secondsLeft--;
    updateTimerDisplay();
    if (session.secondsLeft <= 0) {
      stopTimer();
      submitExam();
    }
  }, 1000);
}
function stopTimer() { clearInterval(session.timerInterval); }
function updateTimerDisplay() {
  const m = Math.floor(session.secondsLeft / 60);
  const s = session.secondsLeft % 60;
  const el = document.getElementById('timer');
  el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  el.classList.toggle('warn', session.secondsLeft <= 300);
}

// ══════════════════════════════════════════════════════════
//  RESULTS
// ══════════════════════════════════════════════════════════
function showResults() {
  showScreen('results');

  const qs = session.questions;
  let correct = 0;
  qs.forEach((q, i) => {
    if (session.answers[i] === q.correctShuffledIdx) correct++;
  });
  const pct = Math.round(correct / qs.length * 100);
  const pass = pct >= 60;

  // Score circle
  document.getElementById('score-circle-wrap').innerHTML =
    `<div class="score-circle ${pass?'pass':'fail'}">${pct}%</div>`;
  document.getElementById('score-summary').textContent =
    `${correct} / ${qs.length} correct · ${pass?'Likely Pass':'Below Pass Mark'} (reference: 60%)`;

  // Subject breakdown
  const subjMap = {};
  qs.forEach((q,i) => {
    if (!subjMap[q.subject]) subjMap[q.subject] = {correct:0,total:0};
    subjMap[q.subject].total++;
    if (session.answers[i] === q.correctShuffledIdx) subjMap[q.subject].correct++;
  });

  const tbody = document.getElementById('subj-table-body');
  tbody.innerHTML = '';
  for (const [subj, data] of Object.entries(subjMap).sort((a,b)=>a[0].localeCompare(b[0]))) {
    const p = Math.round(data.correct/data.total*100);
    const low = p < 60;
    tbody.innerHTML += `<tr>
      <td>${subj}</td>
      <td>${data.correct}/${data.total}</td>
      <td><span class="pct-badge ${low?'low':'ok'}">${p}%</span></td>
      <td><div class="subj-bar"><div class="subj-bar-fill ${low?'low':''}" style="width:${p}%"></div></div></td>
    </tr>`;
  }

  // Question review
  const reviewList = document.getElementById('review-list');
  reviewList.innerHTML = '';
  qs.forEach((q,i) => {
    const userAns = session.answers[i];
    const isCorrect = userAns === q.correctShuffledIdx;
    const isSkipped = userAns === null;
    const statusClass = isSkipped ? 'skipped' : isCorrect ? 'correct' : 'wrong';
    const statusText  = isSkipped ? '–' : isCorrect ? '✓' : '✗';

    const div = document.createElement('div');
    div.className = 'review-q';

    let optHtml = '';
    q.shuffledOptions.forEach((opt, li) => {
      let cls = 'neutral';
      if (li === q.correctShuffledIdx) cls = 'correct-ans';
      else if (li === userAns)         cls = 'user-wrong';
      optHtml += `<div class="review-option ${cls}">
        <span class="ol">${LETTERS[li]}</span>
        <span>${escHtml(opt)}${li===q.correctShuffledIdx?' ✓ Correct Answer':''}</span>
      </div>`;
    });

    div.innerHTML = `
      <div class="review-q-header" onclick="toggleReview(this)">
        <div class="q-status ${statusClass}">${statusText}</div>
        <div class="q-num">Q${i+1}</div>
        <div class="q-snippet">${escHtml(q.question_text.substring(0,100))}…</div>
        <div class="q-subj">${q.subject}</div>
      </div>
      <div class="review-q-body">
        <div class="q-text">${escHtml(q.question_text)}</div>
        ${optHtml}
      </div>`;
    reviewList.appendChild(div);
  });
}

function toggleReview(header) {
  header.nextElementSibling.classList.toggle('open');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('btn-print').addEventListener('click', () => window.print());
document.getElementById('btn-new-session').addEventListener('click', () => {
  stopTimer();
  showScreen('setup');
  buildBankSummary();
  document.getElementById('dash-loading').style.display = 'block';
  document.getElementById('dash-content').style.display = 'none';
  fetchSessions().then(renderDashboard);
});

// ══════════════════════════════════════════════════════════
//  CALCULATOR
// ══════════════════════════════════════════════════════════
let calcState = { display: '0', prev: null, op: null, resetNext: false };

function calcAction(key) {
  const s = calcState;
  if (key === 'C') {
    Object.assign(s, { display:'0', prev:null, op:null, resetNext:false });
  } else if (key === '⌫') {
    s.display = s.display.length > 1 ? s.display.slice(0,-1) : '0';
  } else if (['+','-','*','/','%'].includes(key)) {
    if (key === '%') {
      s.display = String(parseFloat(s.display) / 100);
    } else {
      if (s.op && !s.resetNext) {
        s.display = String(calcOp(parseFloat(s.prev), parseFloat(s.display), s.op));
      }
      s.prev = s.display; s.op = key; s.resetNext = true;
    }
  } else if (key === '=') {
    if (s.op) {
      s.display = String(calcOp(parseFloat(s.prev), parseFloat(s.display), s.op));
      s.op = null; s.prev = null; s.resetNext = true;
    }
  } else if (key === '.') {
    if (s.resetNext) { s.display = '0.'; s.resetNext = false; }
    else if (!s.display.includes('.')) s.display += '.';
  } else { // digit
    if (s.resetNext || s.display === '0') { s.display = key; s.resetNext = false; }
    else s.display += key;
  }
  // Prevent display overflow
  const n = parseFloat(s.display);
  let shown = isNaN(n) ? 'Error' : s.display;
  if (shown.length > 12) shown = parseFloat(shown).toPrecision(8);
  document.getElementById('calc-display').textContent = shown;
}

function calcOp(a, b, op) {
  switch(op) {
    case '+': return a+b;
    case '-': return a-b;
    case '*': return a*b;
    case '/': return b===0 ? 'Error' : a/b;
    default:  return b;
  }
}

document.getElementById('btn-calc').addEventListener('click', () => {
  document.getElementById('calculator').classList.toggle('visible');
});

// Draggable calculator
(function() {
  const el = document.getElementById('calculator');
  const bar = document.getElementById('calc-drag-bar');
  let ox, oy, startX, startY;
  bar.addEventListener('mousedown', e => {
    ox = el.offsetLeft; oy = el.offsetTop;
    startX = e.clientX; startY = e.clientY;
    const move = ev => {
      el.style.right = 'auto';
      el.style.bottom = 'auto';
      el.style.left = (ox + ev.clientX - startX) + 'px';
      el.style.top  = (oy + ev.clientY - startY) + 'px';
    };
    const up = () => { document.removeEventListener('mousemove',move); document.removeEventListener('mouseup',up); };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  });
})();
</script>
</body>
</html>
"""

OUTPUT_HTML.write_text(HTML, encoding="utf-8")
print(f"\n✓ Exam HTML written to: {OUTPUT_HTML}")
print(f"  Questions embedded: {len(questions)}")
print(f"\nOpening in browser...")
webbrowser.open(OUTPUT_HTML.as_uri())
