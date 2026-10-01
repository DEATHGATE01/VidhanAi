"""Fill an Act's missing details (number, assent date, commencement, status) from
every legitimate source, and record what each source said.

THE POINT
An Act page that says "Not published by PRS" tells the reader nothing about
whether the value does not exist or nobody looked. The Act number and assent date
of an Act of Parliament are public: they are in the Gazette, in India Code, and in
the Act's own PDF. This module searches all of them, writes what it can VERIFY,
and otherwise stores a note saying which sources were consulted, on what date, and
what each one answered -- so "unknown" becomes evidence of a search instead of an
excuse.

SOURCES, IN ORDER OF AUTHORITY
  1. India Code (indiacode.gov.in DSpace REST, via enrich_indiacode's matcher) --
     official database: number, assent date, commencement, repealed flag.
  2. The Act's own PDF (pdf_url; Gazette header) -- the published text of the Act.
  3. Wikipedia + DuckDuckGo -- corroboration only. A number found on the open web
     is written ONLY when two independent sources agree on the same
     number/year, or when one agrees with a year the authoritative sources
     already pin. Otherwise it is recorded in the note and NOT written.

HONESTY CONTRACT
- A value is written only from source 1 or 2, or from source 3 under the
  two-source agreement rule above. Never a single unsourced web hit, never a
  "close enough" year, never a guess.
- `acts.evidence` holds the exact matched line/field for every value written.
- `acts.lookup_note` + `acts.details_checked_at` record the full search result
  even when nothing was found, so the UI can say what was tried and when.
- Every failure mode (offline, non-PDF, no match, disagreeing sources) is
  reported per Act; nothing is silently skipped.

Usage (from `backend/`):

    python scripts/maintenance/enrich_act_details.py --dry-run --limit 5
    python scripts/maintenance/enrich_act_details.py                    # all acts
    python scripts/maintenance/enrich_act_details.py --act-ids 6,15 --refresh

Do NOT run two copies of this at once. It is idempotent and safe to re-run, but
two concurrent --refresh runs race on the same rows and the last writer wins: a
run started against older parsing logic can silently overwrite a value a later run
corrected. (Observed 2026-10-01: two overlapping runs both writing assent dates;
the corrected values survived only because the older run finished first.)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from scripts.maintenance.enrich_indiacode import discover_india_code_record  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
MAX_PDF_BYTES = 25 * 1024 * 1024
PDF_FIRST_PAGES = 3

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

_RE_NUMBER = re.compile(r"\b(?:ACT\s+)?NO\.?\s*(\d{1,3})\s+OF\s+(\d{4})\b", re.I)
_RE_ASSENT_PROSE = re.compile(
    r"received\s+the\s+assent\s+of\s+the\s+President\s+on\s+the\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s*(\d{4})", re.I)
_RE_ASSENT_BRACKET = re.compile(
    r"\[\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s*(\d{4})\s*\.?\s*\]")
_RE_BILL_NO = re.compile(r"\bBill\s+No\.?\s*([0-9A-Za-z\-]+)\s+of\s+(\d{4})", re.I)


def _parse_date(day: str, month: str, year: str):
    m = MONTHS.get(month.strip().lower())
    if not m:
        return None
    try:
        return datetime(int(year), m, int(day))
    except ValueError:
        return None


def _clean(s) -> str:
    return " ".join(str(s or "").split())


# ---------------------------------------------------------------------------
# Tier 2: the Act's own PDF
# ---------------------------------------------------------------------------

def pdf_text(url: str, session: requests.Session, timeout: int = 120):
    if not url:
        return None, "no pdf_url"
    try:
        resp = session.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return None, f"download failed ({type(exc).__name__})"
    if resp.status_code != 200:
        return None, f"download HTTP {resp.status_code}"
    content = resp.content[:MAX_PDF_BYTES]
    if not content.startswith(b"%PDF"):
        return None, "not a PDF"
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return None, "pdftotext not installed"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(content)
            tmp_path = fh.name
        proc = subprocess.run(
            [pdftotext, "-f", "1", "-l", str(PDF_FIRST_PAGES), "-layout", tmp_path, "-"],
            capture_output=True, text=True, errors="replace", timeout=120)
        text = proc.stdout or ""
        return (text, "ok") if text.strip() else (None, "no text (scanned PDF?)")
    except subprocess.TimeoutExpired:
        return None, "pdftotext timed out"
    except Exception as exc:  # pragma: no cover
        return None, f"pdf handling failed ({type(exc).__name__})"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def from_pdf(text: str, act_year):
    """Return (fields, note_fragment) from Gazette text."""
    fields: dict = {}
    evidence: list[str] = []
    notes: list[str] = []

    for m in _RE_NUMBER.finditer(text):
        number, year = int(m.group(1)), m.group(2)
        if act_year and year != str(act_year):
            continue
        if number == 0 or number > 500:
            continue
        fields["act_number"] = str(number)
        evidence.append(f"Act number from PDF: '{_clean(m.group(0))}'")
        break
    if "act_number" not in fields:
        bill = _RE_BILL_NO.search(text)
        if bill:
            notes.append(f"PDF is the Bill text (Bill No. {bill.group(1)} of {bill.group(2)}); no Act number in it")

    assent = None
    m = _RE_ASSENT_PROSE.search(text)
    if m:
        assent = _parse_date(m.group(1), m.group(2), m.group(3))
        if assent:
            evidence.append("Assent from PDF: '" + _clean(m.group(0)) + "'")
    if assent is None:
        m = _RE_ASSENT_BRACKET.search(text)
        if m:
            assent = _parse_date(m.group(1), m.group(2), m.group(3))
            if assent:
                evidence.append("Assent from PDF bracketed date: '" + _clean(m.group(0)) + "'")
    if assent:
        fields["assent_date"] = assent
    fields["_evidence"] = " | ".join(evidence)
    fields["_notes"] = notes
    return fields, " | ".join(notes)


# ---------------------------------------------------------------------------
# Tier 3: open-web corroboration (never authoritative on its own)
# ---------------------------------------------------------------------------

def wikipedia_lookup(title: str, session: requests.Session):
    """Return (number, year) if the Wikipedia article states 'Act No. n of yyyy'."""
    try:
        resp = session.get("https://en.wikipedia.org/w/api.php", timeout=45, params={
            "action": "query", "format": "json", "prop": "revisions", "rvprop": "content",
            "rvslots": "main", "titles": title, "redirects": 1,
        })
        pages = (resp.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            rev = (page.get("revisions") or [{}])[0]
            content = ((rev.get("slots") or {}).get("main") or {}).get("*") or ""
            hits = _RE_NUMBER.findall(content[:8000])
            if hits:
                return (hits[0][0], hits[0][1]), f"Wikipedia '{page.get('title')}' says NO. {hits[0][0]} OF {hits[0][1]}"
        return None, f"Wikipedia has no 'Act No. n of yyyy' for '{title}'"
    except Exception as exc:
        return None, f"Wikipedia lookup failed ({type(exc).__name__})"


def ddg_lookup(title: str, session: requests.Session):
    """Return (number, year) if a web search snippet states 'Act No. n of yyyy'."""
    try:
        resp = session.get("https://html.duckduckgo.com/html/",
                           params={"q": f'"{title}" "Act No" of'}, timeout=45)
        if resp.status_code != 200:
            return None, f"web search HTTP {resp.status_code}"
        text = re.sub(r"<[^>]+>", " ", resp.text)
        hits = _RE_NUMBER.findall(text)
        if hits:
            return (hits[0][0], hits[0][1]), f"web search snippet says NO. {hits[0][0]} OF {hits[0][1]}"
        return None, "web search returned no 'Act No. n of yyyy' snippet"
    except Exception as exc:
        return None, f"web search failed ({type(exc).__name__})"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def gather(act, session: requests.Session, want_web: bool = True):
    """Consult every source for one Act. Returns (fields, note_lines)."""
    fields: dict = {}
    notes: list[str] = []
    evidence: list[str] = []

    # --- 1. India Code (authoritative) ---
    record, reason = discover_india_code_record(session, act.title, act.year)
    ic_enact = None
    if record is None:
        notes.append(f"India Code: {reason}")
    else:
        md = record["metadata"]
        first = lambda k: ((md.get(k) or [{}])[0] or {}).get("value")  # noqa: E731
        number = first("dc.identifier.act_number")
        if number:
            fields["act_number"] = str(number)
            evidence.append(f"India Code: dc.identifier.act_number = {number!r} ({record['item_url']})")
        # India Code publishes NO assent-date field. dc.date.enact_date (==
        # dc.date.issued) is the enactment/issue date and must NOT be written into
        # assent_date: that silently reports a passing date as an assent date.
        # It is kept aside and only ever used as a last resort, labelled as what
        # it is.
        enacted = first("dc.date.enact_date")
        if enacted:
            try:
                ic_enact = datetime.fromisoformat(str(enacted)[:10])
                notes.append(
                    f"India Code: dc.date.enact_date = {ic_enact.date()} "
                    "(enactment/issue date; India Code publishes no assent date)")
            except ValueError:
                pass
        enforce = first("dc.date.enforcement_date")
        if enforce:
            try:
                fields["commencement_date"] = datetime.fromisoformat(str(enforce)[:10])
                evidence.append(f"India Code: dc.date.enforcement_date = {enforce!r}")
            except ValueError:
                pass
        repealed = str(first("dc.identifier.repealed") or "").strip().lower()
        if repealed in ("true", "false"):
            fields["status"] = "repealed" if repealed == "true" else "in_force"
            evidence.append(f"India Code: dc.identifier.repealed = {repealed!r} -> {fields['status']}")
        fields["source_url"] = record["item_url"]
        notes.append(f"India Code: matched record (no. {number}, year {act.year})")
        fields["_matched_indiacode"] = True

    # --- 2. The Act's own PDF (authoritative) ---
    text, pdf_reason = pdf_text(act.pdf_url, session)
    if text is None:
        notes.append(f"Act PDF: {pdf_reason}")
    else:
        pdf_fields, pdf_note = from_pdf(text, act.year)
        notes.append("Act PDF: " + (pdf_note or "Gazette header parsed"))
        if pdf_fields.get("_evidence"):
            evidence.append(pdf_fields["_evidence"])
        for key in ("act_number", "assent_date"):
            if key in pdf_fields and key not in fields:
                fields[key] = pdf_fields[key]

    # --- Assent: the Act's own words win; a conflict is recorded, not hidden ---
    pdf_assent = pdf_fields.get("assent_date") if text is not None else None
    if pdf_assent and ic_enact and pdf_assent.date() != ic_enact.date():
        # Two authoritative sources disagree. Keep the Act's own text (it is the
        # document that receives the assent) and say so, with both dates.
        notes.append(
            f"CONFLICT: Act PDF assent {pdf_assent.date()} vs India Code "
            f"dc.date.enact_date {ic_enact.date()} - using the Act's own text")
        evidence.append(
            f"Conflict recorded: Act PDF assent {pdf_assent.date()} vs India Code "
            f"enact_date {ic_enact.date()} (enactment dates and assent dates differ)")
        fields["assent_date"] = pdf_assent
    elif "assent_date" not in fields and ic_enact:
        # No assent sentence anywhere: fall back to the enactment date, labelled.
        fields["assent_date"] = ic_enact
        evidence.append(
            f"Assent date not published in any source; showing India Code "
            f"dc.date.enact_date = {ic_enact.date()} (enactment date, not an assent date)")
        notes.append("Assent: fell back to India Code enactment date (labelled in evidence)")

    # --- 3. Open web, corroboration only ---
    if want_web and "act_number" not in fields:
        wiki, wiki_note = wikipedia_lookup(act.title, session)
        notes.append(wiki_note)
        ddg, ddg_note = ddg_lookup(act.title, session)
        notes.append(ddg_note)
        votes = {}
        for src in (wiki, ddg):
            if src:
                votes[src] = votes.get(src, 0) + 1
        agreed = [v for v, n in votes.items() if n >= 2]
        if agreed:
            number, year = agreed[0]
            if not act.year or year == str(act.year):
                fields["act_number"] = str(number)
                evidence.append(f"Web corroboration (2 independent sources agree): NO. {number} OF {year}")
                notes.append(f"ACCEPTED web number {number} of {year} (two sources agree)")
            else:
                notes.append(f"REJECTED web number {number} of {year}: year disagrees with {act.year}")
        elif any(votes):
            notes.append("web number seen on only one source — not written (needs two to agree)")

    fields["_evidence"] = " | ".join([e for e in evidence if e])
    return fields, notes


def parse_args():
    p = argparse.ArgumentParser(description="Fill Act details from every legitimate source, recording what each said.")
    p.add_argument("--act-ids", type=str, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--refresh", action="store_true", help="revisit acts that already have a number")
    p.add_argument("--no-web", action="store_true", help="skip the web corroboration tier")
    p.add_argument("--delay", type=float, default=0.6)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with app.app_context():
        query = Act.query
        if args.act_ids:
            ids = [int(x) for x in args.act_ids.split(",") if x.strip()]
            query = query.filter(Act.id.in_(ids))
        elif not args.refresh:
            query = query.filter((Act.act_number == None) | (Act.assent_date == None))  # noqa: E711
        acts = query.order_by(Act.year.desc(), Act.id).all()
        if args.limit:
            acts = acts[: args.limit]
        print(f"acts to process: {len(acts)}")

        stats = {"filled": 0, "partial": 0, "nothing": 0}
        for idx, act in enumerate(acts, 1):
            try:
                fields, notes = gather(act, session, want_web=not args.no_web)
            except Exception as exc:
                stats["nothing"] += 1
                print(f"  [!!] {act.id:4d} {act.title[:48]:48s} {type(exc).__name__}: {exc}")
                time.sleep(args.delay)
                continue

            got = [k for k in ("act_number", "assent_date", "commencement_date", "status") if fields.get(k)]
            label = "filled" if len(got) >= 2 else ("partial" if got else "nothing")
            stats[label if label != "nothing" else "nothing"] = stats.get(label, 0) + (1 if label != "nothing" else 0)
            print(f"  [{label:7s}] {act.id:4d} {act.title[:40]:40s} " + (
                f"no={fields.get('act_number')} assent="
                f"{fields['assent_date'].date() if fields.get('assent_date') else None} "
                f"comm={fields['commencement_date'].date() if fields.get('commencement_date') else None} "
                f"status={fields.get('status')}" if got else "no source could fill anything"))

            if not args.dry_run:
                for key in ("act_number", "assent_date", "commencement_date", "status"):
                    if fields.get(key):
                        setattr(act, key, fields[key])
                if fields.get("_matched_indiacode"):
                    act.source = "indiacode"
                    act.source_url = fields.get("source_url") or act.source_url
                elif fields.get("act_number") or fields.get("assent_date"):
                    act.source = "prs_act_pdf"
                if fields.get("_evidence"):
                    act.evidence = fields["_evidence"]
                act.lookup_note = " | ".join(notes)[:2000]
                act.details_checked_at = datetime.utcnow()
                if idx % 10 == 0:
                    db.session.commit()
            time.sleep(args.delay)

        if not args.dry_run:
            db.session.commit()
        print("\nSUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
        print("act_number:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM acts WHERE act_number IS NOT NULL")).scalar(), "/50",
            "| assent:", db.session.execute(db.text(
                "SELECT COUNT(*) FROM acts WHERE assent_date IS NOT NULL")).scalar(), "/50",
            "| commencement:", db.session.execute(db.text(
                "SELECT COUNT(*) FROM acts WHERE commencement_date IS NOT NULL")).scalar(), "/50",
            "| status known:", db.session.execute(db.text(
                "SELECT COUNT(*) FROM acts WHERE status IS NOT NULL AND status != 'unknown'")).scalar(), "/50")
    return 0


if __name__ == "__main__":
    sys.exit(main())
