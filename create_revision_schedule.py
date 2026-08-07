#!/usr/bin/env python3
"""
SQE1 Revision Schedule Generator — COLP-gated
───────────────────────────────────────────────────────────────
Reads your COLP calendar, maps each scheduled session to a
revision companion chapter, then fills FREE days ONLY with
chapters that have already been taught in COLP.

Each free day gets:
  • One revision companion chapter block  (09:00–10:30, 90 min)
  • One 30-min FLK1/FLK2 mock session    (11:00–11:30)

Run:
  python3 create_revision_schedule.py          → generate schedule
  python3 create_revision_schedule.py --list   → show all COLP events
"""

import urllib.request, urllib.error, re, uuid, sys, json, ssl
from datetime import date, datetime, timedelta
from pathlib import Path

# macOS Python often lacks the system CA bundle; bypass verification for this read-only fetch
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

ICS_URL = (
    "https://collegalpractice.instructure.com/feeds/calendars/"
    "user_3kjivvRvAN2pXJ5kWDmrdYh0cXp6tgdTEJ7iKG4K.ics"
)

SCRIPT_DIR = Path(__file__).parent

# ══════════════════════════════════════════════════════════════════════
#  REVISION COMPANION CHAPTERS
#  Each entry: (subject_name, paper, chapter_id, chapter_title, keywords)
#  keywords = words/phrases that should appear in the COLP event title
#  to count as "this chapter has been taught"
# ══════════════════════════════════════════════════════════════════════
CHAPTERS = [
    # ── Contract Law (FLK1) ──────────────────────────────────────────
    ("Contract Law", "FLK1", "1.1", "Offer & Acceptance",
     ["offer", "acceptance", "invitation to treat", "itclr", "contract formation"]),
    ("Contract Law", "FLK1", "1.2", "Consideration & Promissory Estoppel",
     ["consideration", "estoppel", "promissory"]),
    ("Contract Law", "FLK1", "1.3", "Intention to Create Legal Relations & Capacity",
     ["intention", "legal relation", "capacity", "itclr"]),
    ("Contract Law", "FLK1", "1.4", "Terms of the Contract",
     ["terms", "condition", "warranty", "innominate", "express", "implied term"]),
    ("Contract Law", "FLK1", "1.5", "Exclusion Clauses & Unfair Terms",
     ["exclusion", "unfair", "ucta", "limitation clause"]),
    ("Contract Law", "FLK1", "1.6", "Misrepresentation",
     ["misrepresentation", "misrep"]),
    ("Contract Law", "FLK1", "1.7", "Duress, Undue Influence & Illegality",
     ["duress", "undue influence", "illegality", "restraint of trade"]),
    ("Contract Law", "FLK1", "1.8", "Discharge & Breach",
     ["discharge", "breach", "frustration", "performance"]),
    ("Contract Law", "FLK1", "1.9", "Remedies for Breach",
     ["remedies", "damages", "specific performance", "injunction", "remoteness"]),

    # ── Tort (FLK1) ─────────────────────────────────────────────────
    ("Tort", "FLK1", "2.1", "Negligence — Duty of Care & Breach",
     ["negligence", "duty of care", "breach", "caparo", "bolam"]),
    ("Tort", "FLK1", "2.2", "Negligence — Causation & Damage",
     ["causation", "remoteness", "but for", "psychiatric", "pure economic"]),
    ("Tort", "FLK1", "2.3", "Occupiers' Liability",
     ["occupier", "visitor", "trespasser", "occupiers"]),
    ("Tort", "FLK1", "2.4", "Nuisance & Rylands v Fletcher",
     ["nuisance", "rylands", "fletcher", "private nuisance", "public nuisance"]),
    ("Tort", "FLK1", "2.5", "Defamation",
     ["defamation", "libel", "slander"]),
    ("Tort", "FLK1", "2.6", "Vicarious Liability",
     ["vicarious", "employer", "employee liability"]),
    ("Tort", "FLK1", "2.7", "Remedies in Tort",
     ["tort remedies", "damages in tort", "injunction in tort"]),

    # ── Conduct & Ethics (FLK1 + FLK2) ──────────────────────────────
    ("Conduct & Ethics", "BOTH", "3.1", "SRA Principles & Code of Conduct",
     ["sra", "principles", "code of conduct", "conduct", "ethics"]),
    ("Conduct & Ethics", "BOTH", "3.2", "Confidentiality & Legal Privilege",
     ["confidentiality", "privilege", "legal professional privilege"]),
    ("Conduct & Ethics", "BOTH", "3.3", "Conflicts of Interest",
     ["conflict", "own interest", "client conflict"]),
    ("Conduct & Ethics", "BOTH", "3.4", "Duties to the Court",
     ["duty to court", "mislead", "candour", "court duty"]),
    ("Conduct & Ethics", "BOTH", "3.5", "Financial Crime & Money Laundering",
     ["money laundering", "financial crime", "proceeds of crime", "poca", "aml"]),
    ("Conduct & Ethics", "BOTH", "3.6", "Complaints & Regulation",
     ["complaints", "legal ombudsman", "regulation", "sra intervention"]),

    # ── Land Law (FLK2) ─────────────────────────────────────────────
    ("Land Law", "FLK2", "4.1", "Estates & Interests in Land",
     ["estate", "freehold", "leasehold", "legal interest", "equitable interest"]),
    ("Land Law", "FLK2", "4.2", "Registered & Unregistered Land",
     ["registered land", "unregistered land", "land registration", "hm land registry"]),
    ("Land Law", "FLK2", "4.3", "Adverse Possession",
     ["adverse possession", "squatter", "limitation"]),
    ("Land Law", "FLK2", "4.4", "Co-ownership & Trusts of Land",
     ["co-ownership", "joint tenancy", "tenancy in common", "tolata", "trust of land"]),
    ("Land Law", "FLK2", "4.5", "Leases — Creation & Essential Terms",
     ["lease creation", "tenancy", "exclusive possession", "term of years"]),
    ("Land Law", "FLK2", "4.6", "Leases — Covenants & Remedies",
     ["lease covenant", "leasehold covenant", "forfeiture", "lease remedy"]),
    ("Land Law", "FLK2", "4.7", "Easements & Covenants",
     ["easement", "covenant", "right of way", "profit", "freehold covenant"]),
    ("Land Law", "FLK2", "4.8", "Mortgages",
     ["mortgage", "mortgagee", "mortgagor", "equity of redemption"]),

    # ── Criminal Law (FLK2) ─────────────────────────────────────────
    ("Criminal Law", "FLK2", "5.1", "Actus Reus & Mens Rea",
     ["actus reus", "mens rea", "recklessness", "intention", "criminal element"]),
    ("Criminal Law", "FLK2", "5.2", "Offences Against the Person",
     ["assault", "battery", "gbh", "abh", "offence against the person", "wounding"]),
    ("Criminal Law", "FLK2", "5.3", "Property Offences",
     ["theft", "robbery", "burglary", "property offence", "handling stolen"]),
    ("Criminal Law", "FLK2", "5.4", "Fraud & Computer Misuse",
     ["fraud", "computer misuse", "false representation", "fraud act"]),
    ("Criminal Law", "FLK2", "5.5", "Defences",
     ["self-defence", "insanity", "automatism", "intoxication", "consent", "defence"]),
    ("Criminal Law", "FLK2", "5.6", "Inchoate Offences & Accessorial Liability",
     ["inchoate", "attempt", "conspiracy", "accessory", "secondary liability", "aiding"]),

    # ── Trusts Law (FLK2) ───────────────────────────────────────────
    ("Trusts Law", "FLK2", "6.1", "Express Trusts — Three Certainties",
     ["express trust", "three certainties", "certainty of intention", "certainty of subject"]),
    ("Trusts Law", "FLK2", "6.2", "Resulting & Constructive Trusts",
     ["resulting trust", "constructive trust", "common intention"]),
    ("Trusts Law", "FLK2", "6.3", "Trustees — Duties & Powers",
     ["trustee duty", "trustee power", "investment", "delegation"]),
    ("Trusts Law", "FLK2", "6.4", "Beneficiaries & Variation",
     ["beneficiary", "variation of trust", "saunders v vautier"]),
    ("Trusts Law", "FLK2", "6.5", "Breach of Trust & Remedies",
     ["breach of trust", "trust remedy", "tracing", "knowing receipt"]),

    # ── Business Law & Tax (FLK1) ────────────────────────────────────
    ("Business Law & Tax", "FLK1", "7.1", "Business Organisations",
     ["business organisation", "sole trader", "business structure"]),
    ("Business Law & Tax", "FLK1", "7.2", "Partnership",
     ["partnership", "general partnership", "llp", "limited liability partnership"]),
    ("Business Law & Tax", "FLK1", "7.3", "Company Formation",
     ["company formation", "incorporation", "company", "companies house", "articles"]),
    ("Business Law & Tax", "FLK1", "7.4", "Company Constitution & Management",
     ["directors", "company management", "board", "company constitution", "shareholders"]),
    ("Business Law & Tax", "FLK1", "7.5", "Shares & Finance",
     ["shares", "share capital", "finance", "dividend", "debenture"]),
    ("Business Law & Tax", "FLK1", "7.6", "Insolvency",
     ["insolvency", "liquidation", "administration", "winding up", "cvl"]),
    ("Business Law & Tax", "FLK1", "7.7", "Taxation",
     ["tax", "income tax", "corporation tax", "capital gains", "vat", "taxation"]),
    ("Business Law & Tax", "FLK1", "7.8", "Employment Law",
     ["employment", "unfair dismissal", "redundancy", "employment tribunal"]),

    # ── Dispute Resolution (FLK1) ────────────────────────────────────
    ("Dispute Resolution", "FLK1", "8.1", "Civil Procedure — Pre-Action",
     ["pre-action", "pre action protocol", "letter of claim", "civil procedure"]),
    ("Dispute Resolution", "FLK1", "8.2", "Starting a Claim",
     ["claim form", "particulars of claim", "starting claim", "issue claim", "cpr"]),
    ("Dispute Resolution", "FLK1", "8.3", "Interim Remedies & Case Management",
     ["interim", "injunction", "case management", "track allocation", "small claims"]),
    ("Dispute Resolution", "FLK1", "8.4", "Disclosure & Evidence",
     ["disclosure", "standard disclosure", "witness statement", "expert evidence"]),
    ("Dispute Resolution", "FLK1", "8.5", "Trial & Judgment",
     ["trial", "judgment", "costs", "default judgment", "summary judgment"]),
    ("Dispute Resolution", "FLK1", "8.6", "Appeals & Enforcement",
     ["appeal", "enforcement", "enforcement of judgment", "permission to appeal"]),
    ("Dispute Resolution", "FLK1", "8.7", "Alternative Dispute Resolution",
     ["adr", "mediation", "arbitration", "negotiation", "alternative dispute"]),

    # ── Criminal Practice (FLK2) ─────────────────────────────────────
    ("Criminal Practice", "FLK2", "9.1", "Police Powers & PACE",
     ["police powers", "pace", "arrest", "detention", "search", "stop and search"]),
    ("Criminal Practice", "FLK2", "9.2", "Bail",
     ["bail", "remand", "custody time limit"]),
    ("Criminal Practice", "FLK2", "9.3", "Disclosure & Trial Preparation",
     ["criminal disclosure", "cpia", "unused material", "defence statement"]),
    ("Criminal Practice", "FLK2", "9.4", "Magistrates & Crown Court Trial",
     ["magistrates", "crown court", "either way", "indictable", "summary trial"]),
    ("Criminal Practice", "FLK2", "9.5", "Sentencing",
     ["sentencing", "custodial", "community order", "suspended sentence", "fine"]),
    ("Criminal Practice", "FLK2", "9.6", "Appeals",
     ["criminal appeal", "court of appeal", "appeal against conviction", "appeal against sentence"]),

    # ── Legal Services (FLK1) ────────────────────────────────────────
    ("Legal Services", "FLK1", "10.1", "Funding — Legal Aid & CFAs",
     ["legal aid", "cfa", "conditional fee", "funding", "aei"]),
    ("Legal Services", "FLK1", "10.2", "Consumer Credit & Client Care",
     ["consumer credit", "client care", "client care letter", "consumer"]),
    ("Legal Services", "FLK1", "10.3", "Financial Services & Regulation",
     ["financial services", "fsma", "financial regulation", "investment"]),

    # ── Legal System (FLK1) ──────────────────────────────────────────
    ("Legal System", "FLK1", "11.1", "Sources of Law & Court Hierarchy",
     ["sources of law", "court hierarchy", "judicial system", "supreme court"]),
    ("Legal System", "FLK1", "11.2", "Statutory Interpretation",
     ["statutory interpretation", "literal rule", "golden rule", "mischief rule"]),
    ("Legal System", "FLK1", "11.3", "Judicial Precedent",
     ["judicial precedent", "stare decisis", "ratio decidendi", "obiter dicta"]),
    ("Legal System", "FLK1", "11.4", "Human Rights Act",
     ["human rights", "hra", "echr", "convention rights"]),
    ("Legal System", "FLK1", "11.5", "EU Law",
     ["eu law", "european union", "brexit", "retained eu law"]),

    # ── Property Practice (FLK2) ─────────────────────────────────────
    ("Property Practice", "FLK2", "12.1", "Conveyancing — Pre-Contract",
     ["conveyancing", "pre-contract", "searches", "enquiries", "draft contract"]),
    ("Property Practice", "FLK2", "12.2", "Conveyancing — Exchange to Completion",
     ["exchange", "completion", "transfer deed", "land transaction"]),
    ("Property Practice", "FLK2", "12.3", "Leasehold Transactions",
     ["leasehold transaction", "lease assignment", "new lease grant"]),
    ("Property Practice", "FLK2", "12.4", "SDLT & VAT",
     ["sdlt", "stamp duty land tax", "vat on property", "land transaction tax"]),

    # ── Wills & Estates (FLK2) ───────────────────────────────────────
    ("Wills & Estates", "FLK2", "13.1", "Making a Valid Will",
     ["valid will", "testamentary capacity", "execution of will", "attestation"]),
    ("Wills & Estates", "FLK2", "13.2", "Intestacy",
     ["intestacy", "intestate", "intestate succession", "next of kin"]),
    ("Wills & Estates", "FLK2", "13.3", "Probate & Administration",
     ["probate", "grant of probate", "letters of administration", "personal representative"]),
    ("Wills & Estates", "FLK2", "13.4", "Inheritance Tax",
     ["inheritance tax", "iht", "nil rate band", "potentially exempt transfer"]),
    ("Wills & Estates", "FLK2", "13.5", "Inheritance Act Claims",
     ["inheritance act", "family provision", "reasonable financial provision"]),

    # ── Solicitors' Accounts (FLK2) ──────────────────────────────────
    ("Solicitors' Accounts", "FLK2", "SAR.1", "Client Money & Office Money",
     ["client money", "office money", "solicitors accounts", "client account", "sar"]),
    ("Solicitors' Accounts", "FLK2", "SAR.2", "Client Account Rules",
     ["client account rules", "ledger", "receipts", "mixed payment"]),
    ("Solicitors' Accounts", "FLK2", "SAR.3", "Transfers & Receipts",
     ["transfer", "disbursement", "petty cash", "profit costs"]),
    ("Solicitors' Accounts", "FLK2", "SAR.4", "Reporting & Accountants",
     ["accountants report", "reporting accountant", "sar compliance"]),
]


# ══════════════════════════════════════════════════════════════════════
#  ICS PARSING
# ══════════════════════════════════════════════════════════════════════

def fetch_ics(url):
    print("Fetching COLP calendar...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_events(ics_text):
    """Return list of {date, summary, description} dicts, sorted by date."""
    events = []
    # Unfold folded lines (RFC 5545: continuation lines start with space/tab)
    unfolded = re.sub(r'\r?\n[ \t]', '', ics_text)

    for block in re.split(r'BEGIN:VEVENT', unfolded):
        if 'END:VEVENT' not in block:
            continue

        # Date
        dm = re.search(r'DTSTART(?:;[^:\r\n]*)?\s*:\s*(\d{8})', block, re.I)
        if not dm:
            continue
        ds = dm.group(1)
        try:
            evt_date = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
        except ValueError:
            continue

        # Summary
        sm = re.search(r'SUMMARY\s*:\s*(.+)', block, re.I)
        summary = sm.group(1).strip() if sm else ""

        # Description (optional)
        desc_m = re.search(r'DESCRIPTION\s*:\s*(.+?)(?:\r?\n[A-Z])', block, re.I | re.DOTALL)
        description = desc_m.group(1).strip() if desc_m else ""

        if summary:
            events.append({"date": evt_date, "summary": summary, "description": description})

    return sorted(events, key=lambda e: e["date"])


def match_chapter(event_summary, event_description):
    """
    Return list of chapter indices (into CHAPTERS) that this event covers.
    Uses keyword matching against summary + description.
    """
    text = (event_summary + " " + event_description).lower()
    # Strip HTML tags if any
    text = re.sub(r'<[^>]+>', ' ', text)
    matched = []
    for idx, ch in enumerate(CHAPTERS):
        keywords = ch[4]
        if any(kw.lower() in text for kw in keywords):
            matched.append(idx)
    return matched


def build_chapter_unlock_dates(events):
    """
    Return dict: chapter_idx → earliest_date the chapter was covered in COLP.
    If a chapter matches multiple events, use the earliest date.
    """
    unlock = {}
    for evt in events:
        matched = match_chapter(evt["summary"], evt["description"])
        for idx in matched:
            if idx not in unlock or evt["date"] < unlock[idx]:
                unlock[idx] = evt["date"]
    return unlock


# ══════════════════════════════════════════════════════════════════════
#  SCHEDULE BUILDING
# ══════════════════════════════════════════════════════════════════════

MIN_GAP_DAYS = 14   # minimum days between COLP teaching and first revision
SCHEDULE_END = date(2026, 12, 14)   # hard stop for revision calendar

# ── Second pass ───────────────────────────────────────────────────────────
# Chapters taught early are the ones most at risk by January: material first
# seen in March gets one revision touch and is then never revisited. Any free
# day with no newly-unlocked chapter used to be skipped entirely; those days now
# go to a second pass over the earliest-taught chapters, oldest revision first.
EARLY_CUTOFF      = date(2026, 6, 1)   # "taught early" = before this
SECOND_PASS_GAP   = 21                 # min days between the two passes

# ── Full-length sittings ──────────────────────────────────────────────────
# SQE1 is 180 questions per FLK, split into two sittings of 90 questions with
# 2h33m each, on non-consecutive days. A 30-minute daily mock never rehearses
# that; the endurance is a separate skill. These days sit a complete FLK: two
# 153-minute sittings with a break between.
FULL_SITTING_MINUTES = 153
FULL_SITTING_START   = date(2026, 10, 1)   # once enough syllabus is taught
FULL_SITTING_END     = date(2026, 12, 12)  # before the COLP exam on the 15th
FULL_SITTING_COUNT   = 4                   # FLK1, FLK2, FLK1, FLK2


def pick_full_sitting_days(free_days):
    """Evenly spaced free days for full-length papers, alternating FLK1/FLK2."""
    window = [d for d in free_days if FULL_SITTING_START <= d <= FULL_SITTING_END]
    if not window:
        return []
    n = min(FULL_SITTING_COUNT, len(window))
    step = (len(window) - 1) / max(n - 1, 1)
    out = []
    for i in range(n):
        day = window[int(round(i * step))]
        if day not in [d for d, _ in out]:
            out.append((day, "FLK1" if i % 2 == 0 else "FLK2"))
    return out


def build_schedule(events, free_days):
    """
    For each free day, pick the next unlocked chapter not yet revised.
    Chapters are ordered by their COLP teaching date (not array order),
    and only become eligible MIN_GAP_DAYS after they were first taught.
    Returns list of (day, chapter_idx) or (day, None) if nothing unlocked.
    """
    unlock_dates = build_chapter_unlock_dates(events)

    # Sort chapters by COLP teaching date so revision follows teaching order
    chapter_queue = sorted(
        range(len(CHAPTERS)),
        key=lambda i: unlock_dates.get(i, date.max)
    )
    assignment = []
    used_chapters = []   # chapters already assigned to a free day
    last_revised  = {}   # chapter idx -> date of its most recent revision
    flk_toggle = "FLK1"

    for day in free_days:
        # Find next chapter that: (a) taught at least MIN_GAP_DAYS ago, (b) not yet used
        chosen, pass_no = None, 1
        for idx in chapter_queue:
            if idx in used_chapters:
                continue
            unlock_date = unlock_dates.get(idx)
            if unlock_date and (unlock_date + timedelta(days=MIN_GAP_DAYS)) <= day:
                chosen = idx
                break

        if chosen is None:
            # Nothing new is unlocked. Rather than waste the day, take a second
            # pass over the earliest-taught chapters, least recently revised
            # first, so the March–May material does not go cold.
            candidates = [
                i for i in used_chapters
                if unlock_dates.get(i) and unlock_dates[i] < EARLY_CUTOFF
                and last_revised.get(i)
                and (last_revised[i] + timedelta(days=SECOND_PASS_GAP)) <= day
            ]
            if candidates:
                chosen = min(candidates, key=lambda i: last_revised[i])
                pass_no = 2

        if chosen is not None:
            assignment.append((day, chosen, flk_toggle, pass_no))
            if pass_no == 1:
                used_chapters.append(chosen)
            last_revised[chosen] = day
            flk_toggle = "FLK2" if flk_toggle == "FLK1" else "FLK1"
        # else: nothing eligible at all for this day — skip it

    return assignment


# ══════════════════════════════════════════════════════════════════════
#  ICS OUTPUT
# ══════════════════════════════════════════════════════════════════════

def make_event(summary, description, d, start_hour, start_min, duration_min):
    uid = str(uuid.uuid4())
    start_dt = datetime(d.year, d.month, d.day, start_hour, start_min)
    end_dt   = start_dt + timedelta(minutes=duration_min)
    fmt      = "%Y%m%dT%H%M%S"
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{start_dt.strftime(fmt)}",
        f"DTEND:{end_dt.strftime(fmt)}",
        f"SUMMARY:{summary}",
    ]
    if description:
        lines.append("DESCRIPTION:" + description.replace("\n", "\\n"))
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def write_ics(schedule, out_path):
    ics_events = []

    full_days = dict(pick_full_sitting_days(sorted({d for d, *_ in schedule})))

    for day, ch_idx, mock_paper, *rest in schedule:
        pass_no = rest[0] if rest else 1
        subj, paper, ch_id, ch_title, _ = CHAPTERS[ch_idx]

        # Revision block 09:00–10:30
        tag      = " (2nd pass)" if pass_no == 2 else ""
        rev_sum  = f"SQE1 Revision{tag} - {subj}: {ch_id} {ch_title}"
        rev_desc = (
            f"Subject: {subj} ({paper})\\n"
            f"Chapter: {ch_id} {ch_title}\\n"
            f"Duration: 90 min\\n"
            + ("Second pass — taught before June, revised once already. Test "
               "yourself first, then reread only what you could not recall.\\n"
               if pass_no == 2 else "")
            + f"\\nOpen revision guide: http://127.0.0.1:4321/guide"
        )
        ics_events.append(make_event(rev_sum, rev_desc, day, 9, 0, 90))

        # Full-length paper days replace the short mock with two real sittings
        if day in full_days:
            flk = full_days[day]
            for n, (hh, mm) in enumerate(((9, 0), (13, 30)), start=1):
                ics_events.append(make_event(
                    f"SQE1 FULL PAPER - {flk} sitting {n} of 2 (153 min)",
                    (f"Full-length rehearsal: 90 questions in 2h33m.\\n"
                     f"This is one half of a real {flk} paper; sitting 2 follows "
                     f"after a break, exactly as on the day.\\n"
                     f"Do not stop early and do not check answers between "
                     f"sittings — the point is the endurance.\\n"
                     f"\\nOpen mock exam: http://127.0.0.1:4321/test\\n"
                     f"Select {flk}, source of your choice, and the Full "
                     f"(90 q / 153 min) duration."),
                    day, hh, mm, FULL_SITTING_MINUTES))
            continue

        # Mock session 11:00–11:30
        mock_sum  = f"SQE1 Mock - {mock_paper} (30 min)"
        mock_desc = (
            f"30-minute timed mock session\\n"
            f"Paper: {mock_paper}\\n"
            f"\\nOpen mock exam: http://127.0.0.1:4321/test\\n"
            f"Select {mock_paper} and 30 min duration"
        )
        ics_events.append(make_event(mock_sum, mock_desc, day, 11, 0, 30))

    cal = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ghita SQE1 Revision//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:SQE1 Revision Schedule",
        "X-WR-TIMEZONE:Europe/London",
        *ics_events,
        "END:VCALENDAR",
    ])
    out_path.write_text(cal, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    list_mode = "--list" in sys.argv

    try:
        ics_text = fetch_ics(ICS_URL)
    except Exception as e:
        print(f"ERROR fetching calendar: {e}")
        sys.exit(1)

    events = parse_events(ics_text)
    print(f"Found {len(events)} COLP events")

    if list_mode:
        print("\n── All COLP events ─────────────────────────────────────")
        for evt in events:
            matched = match_chapter(evt["summary"], evt["description"])
            ch_names = [f"{CHAPTERS[i][2]} {CHAPTERS[i][3]}" for i in matched]
            tag = " → " + ", ".join(ch_names) if ch_names else "  [no chapter match]"
            print(f"  {evt['date']}  {evt['summary']}{tag}")
        print()
        print("Run without --list to generate the schedule.")
        return

    # Find date range
    all_dates = [e["date"] for e in events]
    if not all_dates:
        print("No events found in calendar.")
        sys.exit(1)

    today = date.today()
    start = max(min(all_dates), today)

    # Build set of busy days (COLP teaching/seminar days — no revision on these)
    busy = {e["date"] for e in events}

    # Free days = every day up to SCHEDULE_END, not busy, not Saturday (5)
    free_days = []
    d = start
    while d <= SCHEDULE_END:
        if d not in busy and d.weekday() != 5:  # 5 = Saturday
            free_days.append(d)
        d += timedelta(days=1)

    print(f"Programme range: {start} to {SCHEDULE_END}")
    print(f"Free days available: {len(free_days)}")

    # Build schedule (only chapters already unlocked by that free day)
    unlock_dates = build_chapter_unlock_dates(events)
    unmatched = [CHAPTERS[i][3] for i in range(len(CHAPTERS)) if i not in unlock_dates]

    schedule = build_schedule(events, free_days)
    print(f"Revision sessions planned: {len(schedule)}")

    if unmatched:
        print(f"\nNote: {len(unmatched)} chapter(s) had no matching COLP event — excluded:")
        for ch in unmatched[:10]:
            print(f"  • {ch}")
        if len(unmatched) > 10:
            print(f"  … and {len(unmatched)-10} more")
        print("\nRun with --list to see all COLP events and their chapter matches.")

    if not schedule:
        print("\nNo sessions to schedule yet — no free days with unlocked chapters found.")
        sys.exit(0)

    out_path = SCRIPT_DIR / "SQE1_Revision_Schedule.ics"
    write_ics(schedule, out_path)

    print(f"\n✅ Generated {len(schedule)} revision sessions")
    print(f"📄 Saved to: {out_path}")
    print()
    print("Import into Apple Calendar:")
    print(f'  open "{out_path}"')


if __name__ == "__main__":
    main()
