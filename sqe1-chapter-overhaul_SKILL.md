---
name: sqe1-chapter-overhaul
description: Overhaul 3 SQE1 HighYield sections per weekday against the SLK manuals, with mind maps and decision trees
---

Overhaul THREE sections of Ghita's SQE1 revision tool against the official SLK manuals. Work silently: do not report back unless something genuinely needs her decision (see STOP AND ASK below).

## Files
- Tool (the ONLY file to edit): /Users/ghitab/Documents/Claude/Projects/Mission solicitor/SQE1_HighYield_Standalone.html
- Progress tracker: /Users/ghitab/Documents/Claude/Projects/Mission solicitor/overhaul_progress.json
- REVISION SCHEDULE (authoritative): /Users/ghitab/Documents/Claude/Projects/Mission solicitor/SQE1_COLP_Revision.html
- SLK manuals (PDFs): /Users/ghitab/Library/Mobile Documents/com~apple~CloudDocs/GB LEX/Formation Solicitor/
- Bash paths differ: the project folder is /sessions/<session>/mnt/Mission solicitor/ and the manuals are /sessions/<session>/mnt/Formation Solicitor/ — check the Shell access section of your system prompt for the exact prefix.

## 1. Choose the three sections — READ THIS CAREFULLY

Get the schedule from the LIVE PAGE in the browser. It is the only source that is correct. Do this first, every run, before anything else:

    mcp__claude-in-chrome__navigate  https://rfn2jk9dw9-max.github.io/SQE-Prep/SQE1_COLP_Revision.html
    mcp__claude-in-chrome__javascript_tool:
        await new Promise(r=>setTimeout(r,2500));       // let syncFromServer() land
        const a = buildSchedule(done);
        JSON.stringify(Object.entries(a).filter(([k,v])=>v)
                        .sort((x,y)=>x[1].localeCompare(y[1])).slice(0,15));

Take the FIRST THREE codes returned. The numeric part (7.6, 12.3, 8.6) is the section id in the HTML tool. That is the whole picking rule.

### Why it must be the live page
- `web_fetch` returns only a "Loading…" shell — the page is client-rendered. Chrome is the sanctioned escalation.
- The done-set is fetched by the page from `COLP_API` (colp_progress.php) on load and is authoritative. It is NOT in localStorage, NOT in overhaul_progress.json, and `DEFAULT_DONE` in the source is a stale seed (CONT1.1–1.3). Loading the page in Chrome makes the page fetch it for you, which is also the only way to reach that host — its URL is not in the sandbox provenance set, so `web_fetch` will refuse it.
- `overhaul_progress.json` tracks OVERHAUL status. That is a different axis from Ghita's REVISION status. Never use one as the other.

### Do NOT read dates out of the file
`SEED_DATES` in SQE1_COLP_Revision.html is a 117-entry map that looks like a schedule:
  'BUS7.5': '2026-04-21', 'DISP8.4': '...', 'CRMP9.5': '...'
**Those are COLP TEACHING / ASSIGNMENT dates, not revision dates.** Reading them as due dates is a known failure. It produced a fictional "overdue backlog" and sent the 5 Aug 2026 run at 1.5, 2.5 and 12.8 — which the real schedule placed at positions 68–70 of 110, due mid-October, while she was actually on 7.6.

For reference only, `buildSchedule()` computes: seed + MIN_GAP (14 days) → clamped forward to today → snapped to the next free day (`isFreeDay` = not Saturday, not in COLP_BUSY) → greedily spread across remaining free days to SCHED_END (2026-12-14). Two consequences:
- **NOTHING IS EVER OVERDUE.** Every un-done module is re-spread forward from today. There is no backlog. Do not invent one.
- **ORDER IS OLDEST-SEED-FIRST** among un-done modules — the opposite of most-recent-first.
Do not reimplement this in Python; it will drift from the page. Call `buildSchedule` in the page.

### Then
- Take the three in computed-date order, earliest first. Do not skip a section because it is "aligned-needs-visuals" — if it is next, it is next; just don't rewrite prose that is already correct (see §5 for what you SHOULD still fix in one).
- Never redo a section already marked "done" in overhaul_progress.json.

### If the browser is unavailable
STOP AND ASK Ghita for the next three. Do not fall back to SEED_DATES, to DEFAULT_DONE, or to the tracker — every one of those puts you at the wrong end of the queue.

DO NOT USE SQE1_Revision_Schedule.ics OR SQE1_Revision_Tracker.html for scheduling. The .ics is stale (built 3 July on a 65-topic outline) and its numbering does NOT match the manuals — only 7 of 65 entries line up. Using it caused three wrong sections to be overhauled. If you find yourself reading either file to pick sections, stop.

## 2. Extract
Section objects live in a per-subject array in the first <script> block, keyed by subject code (CONT, TORT, COND, LAND, CRML, TRUS, BUS, DISP, CRMP, SERV, SYS, PROP, WILL). Extract one with a brace-matched, escape-aware scan from `{"id":"X.Y"`. The data is valid JS but NOT strict JSON — some sections contain \' escapes, so json.loads will fail on those; handle it or work on the raw string.

Manual chapter numbering matches the section id (6.3 = TRUS6 chapter 6.3). Extract with:
  pdftotext -layout "<manual>.pdf" out.txt
then slice between the chapter heading and the next one. Also check "SLK Manual update BUSINESS TO MARCH 2026...docx" and the other examinable-law update files for anything affecting the chapter, and mark such points as a CURRENCY line.

## 3. Rewrite the notes — TERSE
These are HIGH-YIELD MEMORISATION notes for the SQE exam, not a restatement of the manual.
- Target 15-20k characters for the whole section object. If you approach 40k you have written prose — condense before pushing.
- One point per line. Telegraphic style. Trigger words in CAPS.
- Numbered lists (`{"type":"ol","head":...,"items":[...]}`) for anything countable: four situations, three elements, two limbs.
- Case names in brackets in the notes with NO citation — "(Fowler v Barron)". Full citations go in the `cases` array ONLY. If the manual chapter cites no cases, leave `cases` empty rather than inventing any.
- Mirror the manual's subsections and number the note heads accordingly ("6.3.2.1 Cy-pres").
- Drop the manual's "Summary of Key Principles" block — once the body is a summary it is duplication. The `tip` line is the recap.
- Populate `statutes` (ref + substance); many sections have empty arrays.

## 4. Add visuals — THIS IS THE PRIORITY
Ghita memorises visually. Every section gets a `visuals` ARRAY (not the legacy single `visual`), each entry with a `label` used as the panel heading. Sections 6.3 and 7.5 are the reference implementations — read them first.
- One overview MIND MAP of the whole section, plus one mind map per major topic.
- A DECISION TREE for every pair of doctrines that get confused, and for any multi-stage statutory test.
- Optionally comparison grids and a thresholds grid where numbers must be memorised.
Types: `map` {centre, branches:[{label, leaves:[]}]}; `branch` {nodes:[{q, a:[{k,v}]}]}; also flow, grid, table, ladder {rungs:[{label,desc,color}]}, cards, steps {data:[]}.
Mind map leaves must be 3-6 words. Put counts in the leaf ("AUTOMATIC x4") so the number itself is memorable.

## 5. Rules that must not be broken
- Edit SQE1_HighYield_Standalone.html ONLY. Never create a new version of the file.
- ⚠ MCQ trap notes: preserve the substance. If a trap belongs to a different chapter, MOVE it there — never delete it. You may de-duplicate a trap against the body text and sharpen the wording.
- Drop anything NOT in the manual. Grep each case name back against the manual text before keeping it. Past sections carried invented content (Quistclose, Re Compton, Pemsel, Twinsectra in 6.3; Foss v Harbottle and O'Neill v Phillips in 7.5; a fabricated jurisdiction list in 8.2) that had to be removed.
- Check statutory citations against the manual — they have been wrong before.
- If a section holds content belonging to another section, MOVE it there rather than deleting, unless a dedicated section already covers it better (then drop as superseded and say so in the tracker note). 7.5 is the worked example: share classes went to 7.9, resolutions to 7.8, winding-up priority to 7.14.

## 6. Verify before pushing
Run every section in the file through the renderer in node: extract `esc`, `renderVis` and `buildVis` from the first <script> block, render all sections, and confirm no section produces blank output, no output contains the string "undefined", and every CSS class used has a rule in the <style> block. Also `node --check` the first <script> block (blocks 1 and 2 fail on a pre-existing quirk — ignore those two).

## 7. Push
The sandbox cannot write to the mounted .git. Clone to /tmp instead:
  TOK=$(python3 -c "import json;print(json.load(open('<mnt>/Mission solicitor/secrets.json'))['github_token'])")
  git clone --depth 1 "https://x-access-token:${TOK}@github.com/rfn2jk9dw9-max/SQE-Prep.git" /tmp/pubN
copy the HTML in, `git add SQE1_HighYield_Standalone.html` (that ONE file only — never `git add -A`, the folder holds secrets.json), commit with a message listing the sections and what was wrong with each, and push to main. Use a fresh /tmp directory name each run; old clones may be left root-owned and undeletable.

## 8. Update the tracker
Set each completed section's status to "done", visuals to "array", and put a one-line note on what was wrong (misalignment / bloat / invented content / missing visuals / displaced content and where it went). Update `updated` and `counts`. Save overhaul_progress.json.

## STOP AND ASK
Stay silent on a normal run. Message Ghita only if:
- the manual chapter cannot be found or the numbering does not line up with the section id
- the existing content states something you believe is legally WRONG (not merely absent) — quote it and the manual passage
- content appears to belong to a different chapter and it is not obvious where it should go
- the push fails
Otherwise finish and say nothing.