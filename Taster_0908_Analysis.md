# Progress Taster 09/08 — results analysis

**FLK1 37/50 (74%) · FLK2 31/50 (62%) · Combined 68/100**

SQE1 pass mark historically sits around 55–60%, so FLK1 is comfortable and FLK2 is
marginal. The two papers are not equally weighted in your revision risk: almost
every FLK1 error is isolated, while FLK2's errors cluster.

## Score by subject

| Paper | Subject | Asked | Wrong | Score |
|---|---|---:|---:|---:|
| FLK2 | Trusts | 5 | 3 | 40% |
| FLK1 | Contract | 8 | 4 | 50% |
| FLK2 | Criminal Practice | 7 | 3 | 57% |
| FLK2 | Criminal Liability | 19 | 8 | 58% |
| FLK2 | Property | 5 | 2 | 60% |
| FLK1 | Tort | 8 | 3 | 62% |
| FLK1 | Legal System | 6 | 2 | 67% |
| FLK1 | Business | 7 | 2 | 71% |
| FLK2 | Wills | 4 | 1 | 75% |
| FLK2 | Ethics & Conduct | 4 | 1 | 75% |
| FLK1 | Dispute Resolution | 5 | 1 | 80% |
| FLK2 | Land | 6 | 1 | 83% |
| FLK1 | Ethics & Conduct | 8 | 1 | 88% |
| FLK1 | Legal Services | 8 | 0 | 100% |

## Priority 1 — CRML 5.2, fault and blame (6 of 8 criminal liability errors)

This is the single biggest cluster and the only one where a targeted session
moves the overall score materially. Criminal liability was 19 of the 50 FLK2
questions; at 58% it is dragging the paper down on its own.

Four of the six are **gross negligence manslaughter mechanics**, and the errors
point at one specific misunderstanding — *when* and *against whom* the risk of
death is judged:

- **5.2.4.3** — the seriousness of the risk of death is assessed **at the moment
  the negligence occurred**, not with hindsight. (Doctor who declined the test:
  judged at the point of that decision.)
- **5.2.4.3** — absence of foresight does **not** negate gross negligence.
  Foresight makes grossness *more* likely, but the converse does not follow.
- **5.2.4.1** — a defendant who lacked intent at the time of the act can still
  be liable if a **duty to intervene** arose afterwards (creation-of-danger).
- **5.2.4.2** — where murder and GNM both fail, look for the **alternative
  offence** (aggravated arson) rather than concluding no liability.

Two more on criminal damage:

- **5.2.3** — "damage" is any alteration to the physical nature of property,
  **including reduced usefulness**. It is a question of fact for the jury.
- **5.2.5** — arson needs intention/recklessness **as to damaging property**,
  not foresight of fire.

**Common thread:** you are reading the mens rea requirement as stricter than it
is, and you are stopping at "no liability" where the examiner wants the lesser
or alternative offence. Both are cautious-reasoning habits, not knowledge gaps.

## Priority 2 — Trusts 6.1, certainty of intention (40%, smallest sample)

- **6.1.3.1** — "expectation" is precatory, but read **the clause as a whole**;
  precatory wording elsewhere does not stop a trust arising here.
- **6.1.6.1/2** — you applied the general rule and stopped. The question was
  testing whether an **exception** applied.
- **6.4.3** — trustees must act **unanimously**; a passive trustee can itself be
  a breach.

Only 5 questions, so treat the 40% as a warning flag rather than a measurement.

## Priority 3 — Contract 1.4, termination (FLK1's weakest area)

- **1.4.2.5** — time can **become** of the essence once notice is served.
- **1.4.4.1** — partial performance: quantum meruit is available, but where only
  30% was delivered **repudiation is the better answer**.
- **1.1.4.3** — the postal rule is **displaced** where the letter goes astray
  through the offeree's own carelessness.
- **1.2.3** — blanks (e.g. final price) do not defeat certainty so long as the
  contract provides a mechanism for payment.

## Priority 4 — Criminal Practice 9.3, bail (both errors in one sub-topic)

- **9.3.4.3** — the "no real prospect" test applies **pre-trial and
  post-conviction**.
- **9.3.4.3** — adjournment for reports does **not** remove the right to bail,
  and the presumption expressly applies where a suspended sentence is likely.

You are over-predicting when bail will be refused.

## Recurring failure patterns

1. **Stopping at the general rule.** Trusts 6.1.6, Ethics 3.3.7, Crim 5.2.4.2 —
   in each you picked the orthodox rule where the facts signalled an exception,
   an alternative offence, or a further step.
2. **Over-strict mens rea / over-strict liability tests.** Arson, GBH by
   psychiatric injury (5.1.5.3), indirect force (5.1.5.1), gross negligence.
3. **"Best answer" questions treated as "correct answer" questions.** Ethics
   3.2.1 and 3.3.7 were both marked wrong for incompleteness, not for being
   wrong — you identified a real breach but not the fullest one.
4. **Terminology precision.** Legal System 11.1.6.4 (overruled vs reversed),
   Crim Practice 9.6.3.1 (evidence of *description* is not Turnbull
   identification evidence).

## Solid

Legal Services 8/8, Ethics on FLK1 7/8, Land 5/6, Dispute Resolution 4/5. These
need maintenance revision only.

## What was added to the tools

- **Mock exam bank: 784 → 884 questions.** All 100 taster questions are in, tagged
  by paper (FLK1/FLK2) so paper-specific mocks pick them up.
- **32 new mistake flashcards** in the revision guide, filed to the right chapter
  via the "See x.y.z" reference in each feedback block.
- Two parser bugs fixed along the way, which also corrected **4 pre-existing
  questions** in the bank that had a wrong or missing answer key (see below).

### Parser bugs found and fixed

1. **Answer matching scored `|A∩B| / min(|A|,|B|)`**, which returns a perfect
   1.0 for any option whose words are a subset of the answer text. On short
   options the shorter distractor tied with the real answer and won on index
   order — "LP and LLP only" lost to "LLP only", which was the answer you had
   picked and been marked wrong for. Now uses exact match, then Jaccard.
2. **Options whose second line began with a capital were split into two
   options**, producing six groups; the code kept the first five and silently
   dropped the real fifth. Where the dropped one was your selection, the
   question entered the bank with no answer key at all.
