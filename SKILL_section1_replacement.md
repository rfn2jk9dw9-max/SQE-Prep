# Replacement for §1 of the sqe1-chapter-overhaul task file

SQE1_COLP_Revision.html was rewritten in August 2026. The scheduling constants
in the current task file are out of date, and its sanity check ("two modules per
free day") now FAILS against a correct run — which would trigger a false
STOP AND ASK. Paste the text below over §1 of SKILL.md.

---

## 1. Choose the three sections — READ THIS CAREFULLY

**SEED_DATES in SQE1_COLP_Revision.html are COLP TEACHING dates, NOT revision dates.** Do not treat them as due dates. Doing that on 6 Aug 2026 invented a phantom "~50-section overdue backlog" and produced three wrongly-chosen sections, twice. There is no overdue backlog.

The revision schedule is COMPUTED at page load by `buildSchedule(doneSet)`:
- earliest eligible = SEED_DATES[code] — **there is no MIN_GAP any more**; a module is eligible the day COLP teaches it
- clamped forward to today — so nothing is ever overdue
- snapped to the next free day (`isFreeDay`: not a Saturday, not in COLP_BUSY = all SEED_DATES values ∪ EXTRA_BUSY, **and not one of the four FULL_PAPER_DAYS Sundays**)
- greedily spread across remaining free days to SCHED_END = **2027-01-10** (the day before FLK1 — no longer 2026-12-14, which was the COLP mock), about `ceil(remaining/freeDaysLeft)` per day

Because long-past modules tie at the same clamped `earliest` and the sort is stable, the queue drains in **TEACHING order** — the OLDEST un-revised material is scheduled first.

**There are now TWO sessions a day, and BOTH count.** `buildSchedule` fills the first — one NEW module per free day. `buildSecondPass(assignment, done)` fills the second with spaced REVISITS (SECOND_PASS_GAP 21 days, coldest first by visit count then MODULE_ORDER), which is what puts CONT1.1, TORT2.1, COND3.1, LAND4.1 … back on the calendar. **MERGE the two passes by date and pick from the merged list.** Do NOT take the first pass alone: the revisit slots are the oldest, never-overhauled chapters — precisely the ones the second pass was added to rescue — and ignoring them sends the overhaul to material two to three weeks out while today's chapter goes untouched.

Within a single day, take the first-pass module before the revisit, then `MODULES` order. `getStatus()` colours cards from the first pass only and revisits render on the module's existing card — that is a DISPLAY detail, not a scheduling one, and it is what makes it easy to miss the second pass when reading the page.

**Run the real function; do not reimplement it.** Extract the largest `<script>` block from SQE1_COLP_Revision.html, truncate at the `// ── Render ` comment, strip the `let done = loadDone();` line, replace `let doneDates = loadDoneDates();` with `let doneDates = {};`, and run `buildSchedule` in node. Pass a `localStorage` stub. Verified working recipe:

```js
let src = fs.readFileSync('colp.js','utf8');
src = src.slice(0, src.indexOf('// ── Render '))
         .replace(/let done = loadDone\(\);/, '')
         .replace(/let doneDates = loadDoneDates\(\);/, 'let doneDates = {};');
const mod = {};
new Function('exports','localStorage',
  src + '\nexports.buildSchedule=buildSchedule;exports.buildSecondPass=buildSecondPass;'
      + 'exports.MODULES=MODULES;exports.SEED_DATES=SEED_DATES;'
)(mod, {getItem:()=>null, setItem:()=>{}});
```
Order within a day = `MODULES` order, not alphabetical.

The page subtitle still reads "14-day gap · Ends 14 Dec 2026". **That text is stale — the JS is authoritative.** Do not schedule from the subtitle.

### The done set
`buildSchedule` needs `done`. Try `GET https://bidouillecode.dev/solicitor/colp_progress.php` → `{"done":[...]}` (user_key 'ghita'). If web_fetch refuses the domain, RECONSTRUCT it instead: the done-set is everything taught before the earliest pending module. As at 7 Aug 2026 that was `SEED_DATES[code] < '2026-05-27'` (42 modules). Against the CURRENT file the MERGED schedule opens:

| Date | New module | Revisit |
|---|---|---|
| 7 Aug | PROP12.3 | CONT1.1 |
| 13 Aug | DISP8.6 | TORT2.1 |
| 14 Aug | SYS11.2 | COND3.1 |
| 16 Aug | PROP12.4 | LAND4.1 |
| 20 Aug | WILL13.2 | CRML5.1 |
| 21 Aug | BUS7.7 | TRUS6.1 |
| 23 Aug | DISP8.7 | COND3.2 |

Note `DEFAULT_DONE` is CONT1.1–1.3, but that only seeds the *first* pass — ticked chapters are deliberately INCLUDED in the second pass, so they still come round.

**Sanity-check any reconstruction by confirming it yields ONE module per free day in teaching order, across 75 first-pass days with no module left without a slot.** (The old check was "two modules per free day" — that was correct only while SCHED_END was 2026-12-14 and would now fail against a correct run.) If you cannot fetch AND cannot sanity-check a reconstruction, STOP AND ASK.

### Then pick
Take **Today first, then Upcoming**, in date order — NOT by tracker status. Skip anything already `done` in overhaul_progress.json and move to the next in schedule order. Prefer `todo` over `aligned-needs-visuals` only when choosing between sections on the SAME day; if you take an `aligned-needs-visuals` section, do the visuals pass ONLY and do not rewrite prose that is already correct.

Map code → section id by dropping the subject prefix: BUS7.10 → "7.10", DISP8.10 → "8.10". `MODULES` gives the authoritative chapter TITLE — check it against the tool's title before editing (see §5).

DO NOT USE SQE1_Revision_Schedule.ics OR SQE1_Revision_Tracker.html. The .ics is stale and its numbering does not match the manuals.
