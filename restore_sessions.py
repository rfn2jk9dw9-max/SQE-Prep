#!/usr/bin/env python3
"""
restore_sessions.py — Restores the 5 deleted June sessions from screenshot data,
and corrects today's (30 Jun) session score from 61% (11/18) to 72% (13/18).

Run once from Terminal:
    cd "/Users/ghitab/Documents/Claude/Projects/Mission solicitor"
    python3 restore_sessions.py
"""

import json, urllib.request
from pathlib import Path

API = 'https://bidouillecode.dev/solicitor/progress.php'

def api_get():
    with urllib.request.urlopen(API, timeout=20) as r:
        return json.loads(r.read())

def api_post(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

# Sessions read from screenshot (display times were UTC+1, converted to UTC here).
# No question-level data available — top-level stats only.
DELETED_SESSIONS = [
    # 26 Jun 17:41 display → 16:41 UTC
    {
        'datetime':    '2026-06-26T16:41:00.000Z',
        'paper':       'FLK2',
        'percentage':  89.0,
        'correct':     16,
        'totalQ':      18,
        'durationMode': 0,
        'subjects':    {},
        'questions':   [],
    },
    # 25 Jun 18:29 display → 17:29 UTC
    {
        'datetime':    '2026-06-25T17:29:00.000Z',
        'paper':       'FLK2',
        'percentage':  78.0,
        'correct':     14,
        'totalQ':      18,
        'durationMode': 0,
        'subjects':    {},
        'questions':   [],
    },
    # 1 Jun 20:36 display → 19:36 UTC
    {
        'datetime':    '2026-06-01T19:36:00.000Z',
        'paper':       'FLK2',
        'percentage':  78.0,
        'correct':     14,
        'totalQ':      18,
        'durationMode': 0,
        'subjects':    {},
        'questions':   [],
    },
    # 1 Jun 19:54 display → 18:54 UTC
    {
        'datetime':    '2026-06-01T18:54:00.000Z',
        'paper':       'FLK1',
        'percentage':  78.0,
        'correct':     14,
        'totalQ':      18,
        'durationMode': 0,
        'subjects':    {},
        'questions':   [],
    },
]

def main():
    print("Fetching current server sessions...")
    server = api_get()
    server_dts = {s['datetime']: s for s in server}
    print(f"Server has {len(server)} sessions")

    # 1. Restore the 4 purely-deleted June sessions (not today's)
    for s in DELETED_SESSIONS:
        dt = s['datetime']
        if dt in server_dts:
            print(f"  Already exists: {dt} — skipping")
        else:
            api_post(s)
            print(f"  Restored: {dt} {s['paper']} {s['percentage']}%")

    # 2. Handle today's session (30 Jun) — delete old 61% version, insert corrected 72%
    today_entries = [dt for dt in server_dts if dt.startswith('2026-06-30')]
    for dt in today_entries:
        print(f"  Deleting stale today session: {dt} ({server_dts[dt].get('percentage')}%)")
        api_post({'delete_datetime': dt})

    # Full question breakdown from SQE1 Mock Exam.pdf
    # isCorrect reflects true answers after Q1+Q6 override corrections
    questions = [
        {'num':1,  'subject':'Legal System',                 'isCorrect':True,  'questionText':'A contractual dispute between two roommates is worth a large amount of money. It is also complicated as it involves various third parties. Where is the case likely to be heard at first instance?', 'correctAnswer':'High Court (King\'s Bench Division)', 'userAnswer':'High Court (King\'s Bench Division)'},
        {'num':2,  'subject':'Legal Services',               'isCorrect':False, 'questionText':'A teacher who is unable to drive as they suffer from epilepsy has applied for a job at a private school and was not invited to the second interview. Has the school acted in a discriminatory way?', 'correctAnswer':'Yes, because this treatment could fall within the definition of prohibited conduct in respect of the teacher\'s epilepsy.', 'userAnswer':'No, because there is no prohibited conduct, as the school were acting in a proportionate way to achieve a legitimate aim.'},
        {'num':3,  'subject':'Dispute Resolution',           'isCorrect':True,  'questionText':'A telephone service provider issued a claim against a customer, then assigned its rights to a debt collection company. How should the claim be pursued?', 'correctAnswer':'The debt collection company can be substituted as claimant in place of the telephone service provider.', 'userAnswer':'The debt collection company can be substituted as claimant in place of the telephone service provider.'},
        {'num':4,  'subject':'Dispute Resolution',           'isCorrect':False, 'questionText':'A surveyor served a defence relying on comparable sales data and a named estate agent report. Can the claimant obtain clarification and documents at this stage?', 'correctAnswer':'They can serve a request for further information and obtain a copy of the report, but not any other documents.', 'userAnswer':'They are entitled to copies of the report and documents containing the data relied upon for the valuation.'},
        {'num':5,  'subject':'Ethics and Professional Conduct','isCorrect':True, 'questionText':'A solicitor loses client files on the train and tells colleagues the files are at home. What is the solicitor\'s professional conduct position?', 'correctAnswer':'The solicitor has acted dishonestly in failing to disclose to their colleagues that the files have been left on the train.', 'userAnswer':'The solicitor has acted dishonestly in failing to disclose to their colleagues that the files have been left on the train.'},
        {'num':6,  'subject':'Legal System',                 'isCorrect':True,  'questionText':'Two neighbours had an argument. One neighbour stabbed the other resulting in death. The accused has been charged with murder. Which court is the accused likely to be tried at?', 'correctAnswer':'Crown Court', 'userAnswer':'Crown Court'},
        {'num':7,  'subject':'Tort',                         'isCorrect':True,  'questionText':'A patient with a mental illness refusing a blood transfusion is given one under general anaesthetic. Can the patient recover damages in battery?', 'correctAnswer':'No, because the defence of necessity will apply.', 'userAnswer':'No, because the defence of necessity will apply.'},
        {'num':8,  'subject':'Business Law and Practice',    'isCorrect':True,  'questionText':'An adviser is asked to be the promoter of a new company entering into contracts prior to its formation. What is their liability under a pre-incorporation contract?', 'correctAnswer':'The promoter potentially has personal liability under the pre-incorporation contract.', 'userAnswer':'The promoter potentially has personal liability under the pre-incorporation contract.'},
        {'num':9,  'subject':'Contract Law',                 'isCorrect':True,  'questionText':'A decorator\'s contract was interrupted by a pandemic lockdown. The restaurant owner claims frustration. What is the legal position?', 'correctAnswer':'The contract has been frustrated but the restaurant owner will likely have to pay the decorator a proportion of the fee.', 'userAnswer':'The contract has been frustrated but the restaurant owner will likely have to pay the decorator a proportion of the fee.'},
        {'num':10, 'subject':'Contract Law',                 'isCorrect':False, 'questionText':'A painter abandons a decorating contract halfway through after taking a deposit. What is the legal position?', 'correctAnswer':'The homeowner does not have to pay on a quantum meruit basis for the work as it is only partial performance.', 'userAnswer':'The homeowner is liable to pay the painter on a quantum meruit basis for the work done.'},
        {'num':11, 'subject':'Tort',                         'isCorrect':True,  'questionText':'A parent rushes to hospital after their child\'s road accident. The child recovers. What prevents the parent from claiming for psychological harm?', 'correctAnswer':'The parent has not suffered a recognised psychiatric illness.', 'userAnswer':'The parent has not suffered a recognised psychiatric illness.'},
        {'num':12, 'subject':'Contract Law',                 'isCorrect':False, 'questionText':'A developer threatens a homeowner ("in a pine box") to sell their house. The homeowner signs. What is the likely outcome in contract?', 'correctAnswer':'The resident was subject to duress over the sale. The contract is void.', 'userAnswer':'The resident can elect to have the contract set aside.'},
        {'num':13, 'subject':'Business Law and Practice',    'isCorrect':True,  'questionText':'A retiring partner states they will have no further liability for partnership debts. What is their actual liability?', 'correctAnswer':'The retiring partner will remain liable for the partnership debts because the debts were incurred before their retirement.', 'userAnswer':'The retiring partner will remain liable for the partnership debts because the debts were incurred before their retirement.'},
        {'num':14, 'subject':'Dispute Resolution',           'isCorrect':True,  'questionText':'A farmer defendant faces vague particulars of claim about an alleged verbal contract. What is an appropriate next step?', 'correctAnswer':'Send a written request for specific further information concerning the alleged agreement.', 'userAnswer':'Send a written request for specific further information concerning the alleged agreement.'},
        {'num':15, 'subject':'Ethics and Professional Conduct','isCorrect':True, 'questionText':'A managing partner dismisses a client complaint as baseless without following the firm\'s complaints procedure. What are the professional conduct implications?', 'correctAnswer':'The firm has breached its professional conduct obligations by failing to deal with the complaint in line with its internal procedures and informing the client of their right to complain to the Legal Ombudsman and the SRA.', 'userAnswer':'The firm has breached its professional conduct obligations by failing to deal with the complaint in line with its internal procedures and informing the client of their right to complain to the Legal Ombudsman and the SRA.'},
        {'num':16, 'subject':'Legal Services',               'isCorrect':False, 'questionText':'A software engineer makes offensive comments about a colleague\'s sexual orientation and posts offensive images. What best explains this behaviour?', 'correctAnswer':'The software engineer\'s behaviour is harassment because the conduct is linked to the administrator\'s sexual orientation and affects the administrator\'s dignity.', 'userAnswer':'The software engineer\'s behaviour is harassment because the conduct is linked to the administrator\'s sexual orientation.'},
        {'num':17, 'subject':'Business Law and Practice',    'isCorrect':True,  'questionText':'A private limited company with Model Articles is appointing a new director. What are the governance rules on remuneration and service contract term?', 'correctAnswer':'The board has the authority under the articles to decide directors\' remuneration and shareholder approval is required if the contract gives security of tenure for longer than 2 years.', 'userAnswer':'The board has the authority under the articles to decide directors\' remuneration and shareholder approval is required if the contract gives security of tenure for longer than 2 years.'},
        {'num':18, 'subject':'Tort',                         'isCorrect':True,  'questionText':'A teenager smashes a neighbour\'s car windscreen with a defective sledgehammer and is injured. Can they sue the manufacturer in negligence?', 'correctAnswer':'You cannot sue the manufacturer because you were engaged in illegal activity.', 'userAnswer':'You cannot sue the manufacturer because you were engaged in illegal activity.'},
    ]

    # Build subjects breakdown
    from collections import defaultdict
    subj = defaultdict(lambda: {'correct': 0, 'total': 0})
    for q in questions:
        s = q['subject']
        subj[s]['total'] += 1
        if q['isCorrect']:
            subj[s]['correct'] += 1

    correct_count = sum(1 for q in questions if q['isCorrect'])  # 13
    pct = round(correct_count / len(questions) * 100, 1)         # 72.2

    today_corrected = {
        'datetime':    '2026-06-30T17:55:00.000Z',
        'paper':       'FLK1',
        'percentage':  pct,
        'correct':     correct_count,
        'totalQ':      len(questions),
        'durationMode': 0,
        'subjects':    dict(subj),
        'questions':   questions,
    }
    api_post(today_corrected)
    print(f"  Inserted corrected today session: {correct_count}/{len(questions)} = {pct}% with full question breakdown")

    # 3. Verify
    final = api_get()
    print(f"\nDone. Server now has {len(final)} sessions:")
    for s in sorted(final, key=lambda x: x['datetime'], reverse=True):
        print(f"  {s['datetime']}  {s['paper']}  {s['correct']}/{s['totalQ']}  {s['percentage']}%")

if __name__ == '__main__':
    main()
