"""Read an Act's own official PDF: extract how it commences, and summarize it.

WHY
The Act page showed "Not found — sources checked" for commencement on all 50 Acts,
and had no summary of the Act at all. Both gaps have the same fix: the Act's own
Gazette PDF is already linked from the page, and it states both things in the
document itself.

  1. COMMENCEMENT. Indian Acts commence in one of a few ways, and each is a
     *sourced fact* from the text, not a missing value:
       "shall be deemed to have come into force on the 2nd day of June, 2024"
         -> a real date (here, retrospective commencement)
       "shall come into force on such date as the Central Government may, by
        notification in the Official Gazette, appoint"
         -> commencement by notification: there IS no fixed date to find, and
            saying so is far more useful than "not found"
       "shall come into force at once" / "on the date of publication"
         -> immediate
     A bare "not found" reads as a data defect when the truth was in the document.

  2. SUMMARY. A plain-English summary generated from the Act's own text via the
     same Groq path the bills use, stamped with its model version and the PDF it
     was generated from, so it can never be mistaken for PRS-sourced fact.

HONESTY CONTRACT
- Dates are written only when the Act's text states one; otherwise the provision
  text is stored verbatim-ish in `acts.commencement_note` and the date stays NULL.
- The summary is only saved if a model produced it; a failure saves nothing and
  reports the failure (never a fabricated or silently substituted summary).
- Everything is recorded: which PDF, how many characters of text, which model.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import requests  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
MAX_PDF_BYTES = 25 * 1024 * 1024
PDF_MAX_PAGES = 12          # covers the commencement provision of ordinary Acts
SUMMARY_TEXT_CHARS = 14000  # matches the bill path's 15k ceiling

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}

# --- commencement patterns -------------------------------------------------
_RE_COMMENCE_DATE = re.compile(
    r"(?:shall\s+)?(?:be\s+deemed\s+to\s+)?(?:have\s+)?come[s]?\s+into\s+force\s+"
    r"(?:on|with\s+effect\s+from|from)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"day\s+of\s+([A-Za-z]+),?\s*(\d{4})", re.I | re.S)
_RE_COMMENCE_DATE_ALT = re.compile(
    r"come[s]?\s+into\s+force\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"([A-Za-z]+),?\s*(\d{4})", re.I | re.S)
_RE_BY_NOTIFICATION = re.compile(
    r"come[s]?\s+into\s+force\s+on\s+such\s+date\s+as\s+the\s+"
    r"(?:Central|State)?\s*Government\s+may\b[^.]{0,200}",
    re.I | re.S)
_RE_AT_ONCE = re.compile(
    r"(?:shall\s+)?come[s]?\s+into\s+force\s+(?:at\s+once|immediately|on\s+the\s+"
    r"date\s+of\s+(?:its\s+)?publication)[^.]{0,60}", re.I | re.S)


def fetch_act_text(act, session: requests.Session, timeout: int = 120):
    """Return (text, note). text is the first PDF_MAX_PAGES of the Act's PDF."""
    if not getattr(act, "pdf_url", None):
        return None, "no pdf_url on the act row"
    try:
        resp = session.get(act.pdf_url, timeout=timeout)
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
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(content)
            tmp = fh.name
        out = subprocess.run([pdftotext, "-f", "1", "-l", str(PDF_MAX_PAGES), "-layout", tmp, "-"],
                             capture_output=True, text=True, errors="replace", timeout=150)
        text = out.stdout or ""
        text = re.sub(r"[ \t]+", " ", text)
        return (text, "ok") if text.strip() else (None, "no text layer (scanned PDF?)")
    except subprocess.TimeoutExpired:
        return None, "pdftotext timed out"
    except Exception as exc:  # pragma: no cover
        return None, f"pdf handling failed ({type(exc).__name__})"
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def extract_commencement(text: str):
    """Return (date|None, note|None, evidence|None) for how the Act commences."""
    if not text:
        return None, None, None

    # Match against a whitespace-collapsed copy: these PDFs are two-column, so a
    # phrase like "such date as the Central Government may, by notification ...
    # appoint" can be split across lines. Collapsing recovers the phrase.
    flat = " ".join(text.split())

    for pattern in (_RE_COMMENCE_DATE, _RE_COMMENCE_DATE_ALT):
        m = pattern.search(flat)
        if m:
            day, month_name, year = m.group(1), m.group(2), m.group(3)
            month = MONTHS.get(month_name.strip().lower())
            if month:
                try:
                    when = datetime(int(year), month, int(day))
                except ValueError:
                    continue
                quote = m.group(0)[:220]
                deemed = bool(re.search(r"deemed", m.group(0), re.I))
                note = ("Commencement date stated in the Act"
                        + (" (retrospective: 'shall be deemed to have come into force')" if deemed else ""))
                return when, note, quote

    m = _RE_BY_NOTIFICATION.search(flat)
    if m:
        # These PDFs are two-column, so the RIGHT column's text can bleed into the
        # middle of this sentence (e.g. "... the Central Government may, by 52 of
        # 1962"). Cut the quote at the first stray "N of YYYY" so the evidence
        # reads as the legal phrase rather than layout debris.
        quote = re.split(r"\s\d{1,3}\s+of\s+\d{4}", m.group(0))[0].strip()[:200]
        return None, ("Commences by Central Government notification — the Act fixes no date; "
                      "the Government appoints it in the Official Gazette."), quote

    m = _RE_AT_ONCE.search(flat)
    if m:
        quote = m.group(0)[:220]
        return None, "Commenced on enactment/publication (the Act says it comes into force at once).", quote

    # The document was read and contains no commencement clause (common in
    # amendment Acts, which commence with the principal Act). Saying so is a
    # sourced statement about the text, not a missing value.
    return None, ("No commencement provision in the Act's own text (pages read) — "
                  "amendment Acts often commence when the principal Act does."), None


def append_evidence(act, fragment: str) -> bool:
    """Append a provenance fragment to an Act's evidence, at most once.

    Two runs (an overnight batch and a manual refresh) can overlap on the same
    Act, and a naive `evidence + ' | ' + fragment` appends the same sentence
    twice — which then renders twice in the "Evidence for the values above" line
    on the Act page. Skipping an already-present fragment makes the writers
    idempotent, so re-running any enrichment job is safe.

    Returns True when the fragment was added.
    """
    fragment = (fragment or "").strip()
    if not fragment:
        return False
    current = (act.evidence or "").strip()
    if fragment in current:
        return False
    act.evidence = (f"{current} | {fragment}" if current else fragment)[:2000]
    return True


_RE_BILL_NO = re.compile(r"\bBill\s+No\.?\s*([0-9A-Za-z\-]+)\s+of\s+(20\d\d)", re.I)
# Acts carry a plain integer ("NO. 12 OF 2023"); Bill numbers carry a session/version
# suffix ("No. 139-F of 2026"). That suffix is what tells them apart, and it survives
# where the words "Bill No." do not: these PDFs are two-column, and the layout can
# scramble an adjacent phrase into "AMENDMENT BILL, 2026 (AS PASSED BNY oTH...".
_RE_SUFFIXED_BILL_NO = re.compile(r"\bNo\.?\s*(\d{1,3}-[A-Za-z])\s+of\s+(20\d\d)", re.I)


def extract_bill_number(text: str):
    """Return the Bill number the Act came from, e.g. '105-F of 2026'.

    The Act's own PDF states it (PRS keeps the introduced text in the "Act" file
    for recent Acts). This matters because the Act NUMBER is assigned by the
    Gazette and is often unpublished for months, while the Bill number is known
    from the day it is introduced — it is the same law under its earlier name, so
    showing it is far better than "Act No.: not found".

    The PRS suffix ('-F' in '105-F of 2026', the as-passed version) is kept: it
    distinguishes the as-passed text from the as-introduced one, and dropping it
    would invent a document reference that does not exist.

    The year is whatever the document states, never the Act's own year: a Bill
    introduced in 2024 and passed in 2025 is numbered in 2024.
    """
    if not text:
        return None
    flat = " ".join(text.split())
    m = _RE_BILL_NO.search(flat) or _RE_SUFFIXED_BILL_NO.search(flat)
    return f"{m.group(1)} of {m.group(2)}" if m else None


def derive_status(act):
    """Return (status, basis) for an Act whose status no source states.

    India Code is authoritative for status and has no record for recent years, so
    the honest choices are "unknown" or a derivation that says it is one. Assent is
    a sourced fact from the Act's own text, and an assented Act is in force unless
    a source records its repeal — so we derive `in_force` and record WHY, in words
    the UI shows next to the badge.

    Never overwrites a status that came from an authoritative record. Returns
    (None, None) when nothing can be derived.
    """
    if (act.status or "").lower() == "in_force" and "india code" in (act.evidence or "").lower():
        return None, None  # already sourced — a derivation must not replace it
    if not getattr(act, "assent_date", None):
        return None, None

    def fmt(value):
        return value.strftime("%d %b %Y") if hasattr(value, "strftime") else str(value)[:10]

    parts = [f"the Act received the President's assent on {fmt(act.assent_date)}"]
    if act.commencement_date:
        parts.append(f"it states its commencement as {fmt(act.commencement_date)}")
    elif act.commencement_note:
        parts.append(f"its commencement provision reads: {act.commencement_note.rstrip('.')}")
    basis = ("Derived, not sourced: " + "; ".join(parts)
             + ". No source consulted records its repeal, and India Code has no "
               "record for this year yet.")
    return "in_force", basis


def build_act_summary(act, text: str):
    """Generate a plain-English summary of the Act from its own text.

    Returns (summary_text, model_version) or (None, None) on failure -- never a
    substitute. Uses the same Groq path as bills so behaviour, rate-limit handling
    and provenance stamping stay identical across the product.
    """
    from ai_service import GROQ_MODEL_NAME, generate_groq_summary

    if not text or len(text.strip()) < 400:
        return None, None

    body = text[:SUMMARY_TEXT_CHARS]
    prompt_text = (
        "The following is the official text of an Act of the Indian Parliament "
        "(from its Gazette/PRS PDF). Write a plain-English explanation of the ACT "
        "itself for an interested citizen:\n"
        "- what the Act does and why it exists\n"
        "- who it affects and what changes for them\n"
        "- how and when it comes into force\n"
        "Use only what the text supports: never invent a date, a section number or "
        "an Act number, and if the text does not say something, leave it out.\n\n"
        f"ACT TEXT:\n{body}"
    )
    produced = generate_groq_summary(prompt_text)
    if not produced:
        return None, None
    return produced, f"groq_{GROQ_MODEL_NAME}"
