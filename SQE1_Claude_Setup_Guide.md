# Building your own SQE1 revision tools with Claude
### A COLP student's set-up guide — for the January sitting

You have COLP's SLK manuals, H5P quizzes, Progress Tasters and mock exams. That is a lot of PDF. The problem is not access to material — it's that reading a 300-page manual for the third time doesn't move your score.

This guide gets you three tools built by Claude, from your own COLP files:

1. **A High-Yield companion** — every SLK chapter compressed to one screen of memorisable lines, plus mind maps and decision trees.
2. **A mock exam engine** — your COLP question banks turned into a timed, 180-question exam interface.
3. **A flashcard deck that builds itself** from every question you get wrong.

They are all single HTML files. You open them by double-clicking. No coding.

**Time to build:** one weekend for the first version, then ~20 minutes a week to keep it fed.

---

## Part 0 — Set-up (do this first, ~30 minutes)

- [ ] **Book the exam, if you haven't.** Registration for the January 2027 sitting opens **8 September 2026** and closes **20 November 2026**. The assessment window is **11–22 January 2027**, results **8 March 2027**. London centre slots go early — book the day registration opens.
- [ ] **Download the Claude desktop app** from claude.ai/download. You want the desktop app, not the website — it's the one that can read and write files on your computer.
- [ ] **Subscribe to a paid plan.** The free tier will run out mid-task. Max is worth it if you're building all three tools in one go; Pro is fine if you build over a few weekends.
- [ ] **Make one folder** on your computer called `SQE1`. Everything lives here.
- [ ] **Inside it, make three subfolders:** `Manuals`, `Mock exams`, `Tests`.
- [ ] **Put your COLP files in.** All SLK manuals as PDF in `Manuals`. Anything you've sat — Progress Tasters, mocks, H5P quiz exports — in `Mock exams` or `Tests`.
- [ ] **Open Cowork in the Claude desktop app and connect the `SQE1` folder.** This is the step that matters. Once connected, Claude can read your manuals directly instead of you pasting text.

- [ ] **Get COLP's examinable law updates too.** They issue separate update documents per subject (e.g. "Examinable law update Dispute Resolution"). The January 2027 sitting runs on a revised specification, so a manual dated mid-2026 may be out of date in places. Put the update docs in `Manuals` alongside the PDFs and tell Claude: *"Where an examinable law update contradicts the manual, the update wins — and flag it in the notes so I know it changed."*

> **Naming tip that will save you pain later:** keep COLP's original file names (`SLK LAND4 manual 2026_05_21.pdf`). The subject code and the date in the filename are how Claude works out which manual is which. Don't rename them to "Land Law.pdf".

---

## Part 1 — The High-Yield companion

**What it is:** one HTML file with a chapter for every section of every SLK manual. Each chapter is a page of one-line memorisable points — not prose. Plus mind maps and decision trees drawn as HTML, so you can see the structure of a topic instead of reading about it.

**Why it beats re-reading the manual:** the manual teaches. This revises. Different jobs.

### Step 1.1 — Build the skeleton

- [ ] Start a new chat in Cowork with the `SQE1` folder connected and paste:

```
I'm sitting SQE1 in January. I have the College of Legal Practice SLK
manuals as PDFs in the Manuals folder.

Read the contents pages of every manual and build me a single
self-contained HTML file called SQE1_HighYield.html.

Structure:
- A left-hand sidebar listing every subject, expandable to show each
  numbered section (e.g. 4.1, 4.2, 4.3) exactly as numbered in the manual.
- A main pane that shows the selected section.
- A search box that filters sections by title and by body text.
- Everything inline in the one file - no external CSS, JS or fonts.
  I need to be able to open it offline.

Store the content as a JavaScript array of section objects at the top
of the file, like this:

{
  id: "4.2",
  title: "Freehold Covenants",
  content: "...",
  visuals: [],
  cases: []
}

For now leave content, visuals and cases empty. I just want the
skeleton with the correct section numbering. Tell me how many
sections you found.
```

- [ ] **Check the section numbers against your manuals before going further.** If the numbering is off, every later step inherits the error. This is the single most expensive mistake to fix late.

### Step 1.2 — Fill in the content, one subject at a time

Do **not** ask for all subjects at once. Claude will run out of room and quietly thin the later ones. One subject per message.

- [ ] For each subject, paste this (swapping the manual name):

```
Fill in the content for every section of SLK LAND4.

Rules for the writing - these matter more than anything else:
- These are memorisation notes, not explanation. Assume I have already
  read the manual.
- ONE POINT PER LINE. No paragraphs. No "it is important to note that".
- Aim for 15,000-20,000 characters per section. If you're writing less
  you're leaving out detail; if more, you're explaining rather than listing.
- Lead every rule with the trigger: what fact pattern makes this rule apply?
- Statutory sections and time limits go inline (s 2 LP(MP)A 1989, 12 years,
  21 days). Numbers are what gets tested.
- Case names go in the `cases` array, NOT in the body text. The body should
  read as rules, not as case law commentary.
- Where two things are commonly confused, put them side by side and state
  the distinguishing test in one line.

Show me section 4.1 first so I can check the style before you do the rest.
```

- [ ] Check 4.1. If it's written like a textbook, say **"too much explanation, cut it to bare rules"** and it will recalibrate for the whole subject.
- [ ] Then: `Good. Do the rest of LAND4 the same way.`
- [ ] Repeat for all 15 or so manuals. This is the long part — a few hours spread over a weekend.

### Step 1.3 — Add the visuals

This is the step most people skip and it's the one that does the heavy lifting.

- [ ] For each subject:

```
Now add visuals to every section of LAND4. Populate the `visuals` array.

Two types, rendered as HTML and CSS (no image files, no external libraries):

1. type: "map" - a mind map. Shape:
   { label: "Mind map - the five topics in 4.2",
     type: "map",
     centre: "4.2 FREEHOLD COVENANTS",
     branches: [ { label: "BURDEN AT LAW",
                   leaves: ["Never passes (Austerberry)",
                            "Workarounds: chain of indemnity",
                            "s 79 LPA is word-saving only"] } ] }

2. type: "branch" - a decision tree for anything with a test sequence.
   Each node is a yes/no question with the outcome at each exit.

Rules:
- Every section gets at least one map covering the whole section, plus a
  map per major topic within it.
- Leaves are keywords and section numbers, not sentences.
- Anything that works as a sequence of gates - formalities, passing of
  burden and benefit, elements of a claim - becomes a decision tree.
- CAPITALISE branch labels so the structure reads at a glance.
```

### Step 1.4 — Add the traps (build this in as you go)

Every time you sit a COLP quiz or taster and get something wrong, the wrong answer goes into the file.

- [ ] Export or screenshot the feedback and:

```
Attached is my COLP Progress Taster feedback with the questions I got
wrong. For each one:

1. Work out which section of the HighYield file it belongs to. COLP's
   feedback usually says "See 4.2.3" - use that.
2. Add a trap note at the relevant point in that section's content,
   marked with a warning symbol.
3. The note should name the distractor and say why it's wrong, in one
   or two lines: what I confused with what, and the one test that
   separates them.

Do not rewrite the section. Just insert the trap notes.
```

---

## Part 2 — The mock exam engine

**What it is:** all of COLP's questions in one timed interface — 180 questions, flag-for-review, question navigator, a countdown clock, and a score at the end that tells you which sections you're weak in.

**Why:** SQE1 is 360 single-best-answer questions — FLK1 and FLK2, 180 each, sat on separate days. Each day is **two sessions of 90 questions, 2 hours 33 minutes per session**. That's 1 minute 40 seconds a question, sustained, for two half-days. Doing ten questions at a time in H5P does not prepare you for session two. The stamina is a separate skill from the law.

### Step 2.1 — Extract the question bank

- [ ] Put every mock, taster and quiz PDF into the `Mock exams` folder, then:

```
The Mock exams folder has my COLP mock exams and Progress Tasters as
PDFs. Extract every question into a JSON file.

For each question capture: the full stem, all five options A-E, the
correct answer, COLP's explanation, and the subject or section
reference COLP gives in the feedback.

Watch for these - they will silently corrupt the bank:
- Options that wrap onto a second line get split into two separate
  options, and the last two options get merged. After extracting,
  check every question has exactly five options and flag any that don't.
- The same question appears in more than one PDF. Deduplicate on the
  first 60 characters of the question stem, not on the answer text -
  distractors often share long openings.
- Older PDFs sometimes carry an answer key COLP later corrected. Where
  two copies of the same question disagree on the answer, show me both
  and let me decide.

Report: total questions found, duplicates removed, and anything that
failed the five-option check.
```

- [ ] **Actually read the failure list.** A silently corrupt bank teaches you the wrong law, which is worse than not revising at all.

### Step 2.2 — Build the exam interface

```
Build SQE1_MockExam.html - one self-contained file, everything inline,
with the question bank embedded as a JavaScript array.

Features:
- Start screen: choose FLK1 or FLK2, choose number of questions
  (90 to replicate one real session, 180 for a full paper, or 30 for a
  quick drill), choose subject filter or all.
- Exam screen: one question at a time, five radio options, Next and
  Previous, a Flag for review button, and a question navigator grid
  showing answered / unanswered / flagged.
- A countdown timer set to the real rate: 2 hours 33 minutes per 90
  questions (1 min 40 sec each), scaled to whatever length I pick.
  Show it, don't hide it. Getting used to the clock is the point.
- No feedback during the exam. Score only at the end.
- Results screen: overall score, a breakdown by subject, and a list of
  every question I got wrong with the stem, my answer, the correct
  answer and COLP's explanation.
- Save my score and my wrong answers to browser localStorage so I can
  see my history across sittings.
```

### Step 2.3 — Set the pace

- [ ] One full mock every two weeks from now until December, then one a week in January. Put them in your calendar now, at the actual exam time of day.
- [ ] Sit them cold. No notes, no pausing the timer.

---

## Part 3 — Flashcards that build themselves

**What it is:** every question you ever got wrong, turned into a flashcard, resurfaced until you stop getting it wrong.

**Why:** your wrong answers are the only genuinely personalised revision material you have. Everything else is the same material every other candidate has.

```
Add a flashcard mode to the mock exam file.

Every question I answer incorrectly becomes a flashcard - front is the
stem, back is the correct answer plus the explanation plus the one-line
reason my chosen distractor was wrong.

Important: unlike the exam bank, flashcards should NOT be deduplicated.
If I get the same question wrong three times across three sittings, I
want to see it three times. Repetition of my own errors is the signal.

Add a spaced repetition schedule: after each card I press Again / Hard /
Good / Easy, and the interval adjusts. Cards I press Again on come back
in the same session.

Store progress in localStorage.
```

---

## Part 4 — The weekly loop (this is the actual method)

The tools are scaffolding. This is what makes the score move:

- [ ] **Monday:** work through the week's COLP module as scheduled. Don't skip ahead.
- [ ] **Wednesday:** 30 questions from the mock engine on last week's topic. Cold.
- [ ] **Wednesday, straight after:** feed the wrong answers back into the High-Yield file as trap notes (Step 1.4). Ten minutes.
- [ ] **Friday:** read only the High-Yield chapters for that week, plus the mind map. Not the manual.
- [ ] **Sunday:** flashcard session — whatever the spaced repetition surfaces.
- [ ] **Every second Saturday:** a full timed paper — 90 questions in 2h33 to start with, building to a full 180 (both sessions, one after the other) by November.

### If a score goes *down* after you've revised a topic

This happens and it is alarming. It is almost always not a knowledge gap — it's a **discrimination failure**. You now know more rules, so more of them look plausible, and you're picking between two you can't yet separate.

- [ ] The fix:

```
My score on [topic] went DOWN after revising it. I think I can't
discriminate between the rules rather than not knowing them.

Rebuild this section as a sequence of gates. For each pair of rules I
might confuse, give me the single question that separates them, in the
order I should ask it. Then give me five questions where the only
difference between the right answer and the best distractor is that
one test.
```

---

## Part 5 — Things that will go wrong

Learned the hard way. Read this before you start, not after.

| Problem | What it looks like | Fix |
|---|---|---|
| **Editing the wrong file** | You have `v1`, `v2`, `v2_final`, and your edits vanish | Pick **one** filename and delete the rest. Tell Claude at the start of every chat: "only ever edit SQE1_HighYield.html" |
| **Silent truncation** | You ask for all 15 subjects; subjects 1–4 are excellent, 12–15 are thin | One subject per message. Always. Spot-check the last one. |
| **Answer key drift** | A question's "correct" answer is wrong and you learn the wrong rule | Cross-check anything that surprises you against the SLK manual before you believe it |
| **No backups** | One bad edit and 40 hours are gone | Before any big change: `Make a dated backup copy of the file first.` Or put the folder in Dropbox/iCloud with version history. |
| **Content that reads like a textbook** | Your "high-yield" notes are 8 pages per chapter | Say "too much explanation, cut to bare rules" — early, before it's written 15 subjects that way |
| **Nothing at all happens** | Claude says it's done but the file didn't change | Check the file's modified date. Ask: "Confirm the change is actually in the file — show me the line." |

---

## The one thing to take from this

Don't build all three at once. **Build the mock exam engine first** (Part 2), sit one, and let your wrong answers tell you which subjects need the High-Yield treatment. Building 15 subjects of beautiful notes for topics you're already scoring 80% on is the most common way to waste a month.

Then, roughly:

- **Now → end of September:** mock engine built, sitting one every fortnight, High-Yield for your three weakest subjects only.
- **October → November:** High-Yield for everything else, keeping the fortnightly mocks.
- **December:** flashcards take over. Weekly mocks.
- **January:** mocks and flashcards only. No new content. Nothing new goes in after the first week of January.

Good luck.
