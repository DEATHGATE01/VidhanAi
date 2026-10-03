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

import difflib
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


# ---------------------------------------------------------------------------
# Statute lineage: what an Act amends
#
# An amending Act names its parent statute in its own long title ("An Act further
# to amend the Andhra Pradesh Reorganisation Act, 2014") and again in the operative
# clause ("In the Andhra Pradesh Reorganisation Act, 2014, in section 5, ...").
# Both are authoritative — they are the Act's text, not a summary of it — and they
# are what lets the Act page show the statute's history instead of only the history
# of the 2026 bill that produced it.
#
# CAVEAT: these PDFs are two-column and the text layer interleaves the columns, so
# a capture can come back as "AndhBraILPLradesh Reorganisation Act" (the word split
# by an inserted fragment). We collect every candidate and prefer the clean one; a
# capture that had to be repaired is flagged, never silently trusted.
_RE_AMENDS_TITLE = re.compile(
    r"(?:further\s+to\s+amend|to\s+amend)\s+(?:the\s+)?"
    r"([A-Z][A-Za-z ,()&\-]{4,90}?(?:Act|Adhiniyam|Code|Order))\s*,?\s*((?:1[89]|20)\d\d)",
    re.I)
_RE_AMENDS_IN = re.compile(
    r"\bin\s+the\s+([A-Z][A-Za-z ,()&\-]{4,90}?(?:Act|Adhiniyam|Code|Order))\s*,?\s*"
    r"((?:1[89]|20)\d\d)\s*,?[^A-Za-z]{0,12}\s*in\s+section\s*(\d+[A-Z]?)", re.I)
_RE_SECTION_IN_RANGE = re.compile(r"\bin\s+section\s*(\d+[A-Z]?)\b", re.I)
# The marginal note cites the PARENT's own number beside the amending clause
# ("Act 6 of 2014." next to "In the Andhra Pradesh Reorganisation Act, 2014").
_RE_CITED_ACT_NO = re.compile(r"\bAct\s+(\d+)\s+of\s+((?:1[89]|20)\d\d)\b")
# Clean statute phrases already present in the document, used to REASSEMBLE a name the
# text layer damaged (the leading "In the " the pattern can absorb is stripped below).
_RE_CLEAN_STATUTE_PHRASE = re.compile(
    r"\b[A-Z][a-z]+(?: (?:and |of |the |for )?[A-Za-z()-]{2,}){0,8} (?:Act|Code|Order|Adhiniyam)\b")
# Below this similarity a phrase is a different statute, not a repair: better to say the
# name is unreadable than to print a plausible-looking wrong statute.
REPAIR_MIN_RATIO = 0.82


def _looks_interleaved(name: str) -> bool:
    """True when a capture looks like two columns were interleaved into one word.

    'AndhBraILPLradesh', 'DisBasItLeLr' and 'NationAal' are single tokens carrying a
    capital AFTER the first letter — Indian statute titles are title-case words, so an
    internal capital means the other column was spliced into the word. Such a capture
    is treated as damaged and never used verbatim.
    """
    for token in name.split():
        if re.search(r"^[^A-Za-z]*[A-Za-z][a-z]*(?=[A-Z])[A-Za-z]*[a-z]", token):
            return True
    return False


def _clean_statute_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name or "").strip(" ,.;:")
    name = re.sub(r"^(?:the)\s+", "", name, flags=re.I)
    return name.strip()


def extract_amendment_targets(text: str):
    """Return the statutes an Act says it amends, with the sections it touches.

    Each entry: {title, year, sections, cited_act_number, confidence, evidence}.
    `confidence` is 'clean' when the capture reads as a real title and 'repaired'
    when only a column-interleaved variant was available, so the caller can show
    the difference instead of presenting a mended name as verbatim.
    Returns [] for a principal Act (a new law amends nothing) — a fact about that
    Act, not a failure.
    """
    if not text:
        return []
    flat = re.sub(r"\s+", " ", text)
    candidates = {}

    def add(raw_name, year, section=None):
        name = _clean_statute_name(raw_name)
        if len(name) < 6:
            return None
        key = (re.sub(r"[^a-z]", "", name.lower()), year)
        entry = candidates.setdefault(key, {
            "title": name, "year": year, "sections": [],
            "cited_act_number": None, "interleaved": _looks_interleaved(name),
            "count": 0,
        })
        entry["count"] += 1
        if section and section not in entry["sections"]:
            entry["sections"].append(section)
        if entry["interleaved"] and not _looks_interleaved(name):
            entry["title"], entry["interleaved"] = name, False
        return entry

    for m in _RE_AMENDS_TITLE.finditer(flat):
        add(m.group(1), m.group(2))
    for m in _RE_AMENDS_IN.finditer(flat):
        entry = add(m.group(1), m.group(2), m.group(3))
        if entry is None:
            continue
        window = flat[max(0, m.start() - 40): m.end() + 160]
        for cited in _RE_CITED_ACT_NO.finditer(window):
            if cited.group(2) == m.group(2):
                entry["cited_act_number"] = f"{cited.group(1)} of {cited.group(2)}"
                break
        tail = flat[m.end(): m.end() + 1500]
        nxt = re.search(r"\bin\s+the\s+[A-Z][A-Za-z ,()&\-]{4,90}?(?:Act|Adhiniyam|Code|Order)", tail)
        if nxt:
            tail = tail[:nxt.start()]
        for extra in _RE_SECTION_IN_RANGE.finditer(tail):
            if extra.group(1) not in entry["sections"] and len(entry["sections"]) < 8:
                entry["sections"].append(extra.group(1))

    # A damaged name is reassembled from a cleaner occurrence of the same phrase in the
    # same document; failing that it is FLAGGED, not printed as if it were the statute.
    damaged = [e for e in candidates.values() if e["interleaved"]]
    if damaged:
        phrases = list(dict.fromkeys(_RE_CLEAN_STATUTE_PHRASE.findall(flat)))
        phrases = [re.sub(r"^(?:In the |the )", "", ph) for ph in phrases]
        for entry in damaged:
            best, ratio = None, 0.0
            for ph in phrases:
                r = difflib.SequenceMatcher(None, entry["title"].lower(), ph.lower()).ratio()
                if r > ratio:
                    best, ratio = ph, r
            if best and ratio >= REPAIR_MIN_RATIO:
                entry["title_repaired_from"] = entry["title"]
                entry["title"] = best
                entry["repaired"] = True
                entry["interleaved"] = False   # the name shown is the reassembled one
            else:
                entry["damaged"] = True

    out = []
    for entry in candidates.values():
        if entry.pop("interleaved", False):
            entry["confidence"] = "damaged"
        elif entry.pop("repaired", False):
            entry["confidence"] = "repaired"
        else:
            entry["confidence"] = "clean"
        entry["evidence"] = (
            f"stated in the Act's own text: \"further to amend the {entry['title']}, {entry['year']}\"")
        if entry["confidence"] == "repaired":
            entry["evidence"] += (" — the PDF's two-column text layer spliced this name as "
                                  f"\"{entry.get('title_repaired_from')}\"; it was reassembled from a cleaner "
                                  "occurrence of the same clause in the same document")
        elif entry["confidence"] == "damaged":
            entry["evidence"] += (" — and the text layer spliced the name itself "
                                  f"(read as \"{entry['title']}\"), so this statute is identified by its year "
                                  "and, where the marginal note cites it, its own number")
        out.append(entry)
    # The same statute can appear twice: text-layer damage is not uniform, so one
    # occurrence reads cleanly and another is spliced. Those are one statute — merge
    # them, keeping the best confidence, the union of the sections, and any cited
    # number either occurrence carried.
    ranked = {"clean": 3, "repaired": 2, "damaged": 1}
    merged = {}
    for entry in out:
        key = (re.sub(r"[^a-z]", "", (entry["title"] or "").lower()), entry["year"])
        keep = merged.get(key)
        if keep is None:
            merged[key] = entry
            continue
        better, worse = ((entry, keep) if ranked[entry["confidence"]] > ranked[keep["confidence"]]
                         else (keep, entry))
        better["sections"] = list(dict.fromkeys(better["sections"] + worse["sections"]))
        better["cited_act_number"] = better.get("cited_act_number") or worse.get("cited_act_number")
        better["count"] = better.get("count", 1) + worse.get("count", 1)
        merged[key] = better
    out = list(merged.values())

    # Second pass: a damaged twin and its clean original can still survive as separate
    # entries when the repair did not fire (e.g. the clean phrase is absent from the
    # corpus). Same year + near-identical name means one statute, so keep the readable
    # name and fold the rest in.
    folded = []
    for entry in out:
        norm = re.sub(r"[^a-z]", "", (entry["title"] or "").lower())
        match = None
        for keep in folded:
            if keep["year"] != entry["year"]:
                continue
            kn = re.sub(r"[^a-z]", "", (keep["title"] or "").lower())
            if difflib.SequenceMatcher(None, norm, kn).ratio() >= 0.90:
                match = keep
                break
        if match is None:
            folded.append(entry)
            continue
        better, worse = ((entry, match) if ranked[entry["confidence"]] > ranked[match["confidence"]]
                         else (match, entry))
        better["sections"] = list(dict.fromkeys(better["sections"] + worse["sections"]))
        better["cited_act_number"] = better.get("cited_act_number") or worse.get("cited_act_number")
        better["count"] = better.get("count", 1) + worse.get("count", 1)
        if better is not match:
            folded[folded.index(match)] = better
    out = folded

    out.sort(key=lambda e: (-e["count"], e["year"]))
    for e in out:
        e.pop("count", None)
    return out


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
