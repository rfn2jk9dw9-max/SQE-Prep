#!/usr/bin/env python3
"""
SQE1 Mock Exam — Regenerate
Run this script to re-parse your Tests folder and rebuild SQE1_MockExam.html.
Double-click or run: python3 SQE1_Regenerate.py
"""
import os, subprocess, sys, webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# ── Locate the Tests folder ────────────────────────────────────────────
def find_tests_dir():
    # 1. Same folder as script
    local = SCRIPT_DIR / "Tests"
    if local.exists():
        return local
    # 2. iCloud / Formation Solicitor
    icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
    for candidate in icloud.glob("**/Tests") if icloud.exists() else []:
        return candidate
    # 3. Ask user
    print("Could not automatically locate the Tests folder.")
    path = input("Please enter the full path to your Tests folder: ").strip().strip('"')
    p = Path(path)
    if p.exists():
        return p
    print(f"ERROR: folder not found: {path}")
    sys.exit(1)

def main():
    tests_dir = find_tests_dir()
    print(f"Tests folder: {tests_dir}")

    parser  = SCRIPT_DIR / "parse_questions.py"
    builder = SCRIPT_DIR / "build_exam.py"

    for f in [parser, builder]:
        if not f.exists():
            print(f"ERROR: {f.name} not found next to this script.")
            sys.exit(1)

    # Run builder (which internally runs parser)
    result = subprocess.run(
        [sys.executable, str(builder), str(tests_dir)],
        capture_output=False
    )
    if result.returncode != 0:
        print("Generation failed.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
