"""Resolve a Bill's administering ministry when PRS does not publish one.

Why this exists: PRS bill pages leave ``field-name-field-ministry`` empty for
many bills -- on 2026-09-29 **all 140** tracked bills read ``Unknown`` -- which
made every summary print "Ministry: Unknown" and left the ministry analytics
empty. This module derives a ministry instead of leaving the field blank, and is
explicit (in the database, not just in the UI) about how each value was obtained.

Honesty contract (read this before changing anything here):

* A scraped ministry is the only ``ministry_source='prs'`` value, confidence
  1.0. It is never overwritten by a derived one.
* Values derived here are stamped ``'bill_text'`` (quoted from the bill's own
  text) or ``'llm_inferred'`` (a model's choice from the fixed list below, with
  its rationale stored as evidence). Both are marked inferred in the API payload
  (``ministry_inferred: true``) so a reader can never mistake a guess for a fact.
* The model may answer "Unknown". It may **not** invent a ministry name: its
  answer is rejected unless it is (a) in :data:`UNION_MINISTRIES`, or (b) a
  literal "Ministry of X" / "Department of X" phrase quoted from the bill text.
* Below :data:`MIN_LLM_CONFIDENCE` the result is dropped rather than stored.

Tier order (cheapest and most trustworthy first):

1. ``prs``        -- the PRS bill page (network; one request per bill).
2. ``bill_text``  -- regex over the bill's own full text (free, offline).
3. ``llm_inferred`` -- Groq choosing from the closed list (network; needs a key).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from models import db, Bill, BillContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# The closed candidate list. A derived ministry must be one of these (or an
# exact "Ministry of X" phrase quoted from the bill) -- this is what stops the
# model from inventing a plausible-sounding department.
# ---------------------------------------------------------------------------
UNION_MINISTRIES = (
    "Ministry of Agriculture and Farmers Welfare",
    "Ministry of AYUSH",
    "Ministry of Chemicals and Fertilizers",
    "Ministry of Civil Aviation",
    "Ministry of Coal",
    "Ministry of Commerce and Industry",
    "Ministry of Communications",
    "Ministry of Consumer Affairs, Food and Public Distribution",
    "Ministry of Cooperation",
    "Ministry of Corporate Affairs",
    "Ministry of Culture",
    "Ministry of Defence",
    "Ministry of Development of North Eastern Region",
    "Ministry of Earth Sciences",
    "Ministry of Education",
    "Ministry of Electronics and Information Technology",
    "Ministry of Environment, Forest and Climate Change",
    "Ministry of External Affairs",
    "Ministry of Finance",
    "Ministry of Fisheries, Animal Husbandry and Dairying",
    "Ministry of Food Processing Industries",
    "Ministry of Health and Family Welfare",
    "Ministry of Heavy Industries",
    "Ministry of Home Affairs",
    "Ministry of Housing and Urban Affairs",
    "Ministry of Information and Broadcasting",
    "Ministry of Jal Shakti",
    "Ministry of Labour and Employment",
    "Ministry of Law and Justice",
    "Ministry of Micro, Small and Medium Enterprises",
    "Ministry of Mines",
    "Ministry of Minority Affairs",
    "Ministry of New and Renewable Energy",
    "Ministry of Panchayati Raj",
    "Ministry of Parliamentary Affairs",
    "Ministry of Personnel, Public Grievances and Pensions",
    "Ministry of Petroleum and Natural Gas",
    "Ministry of Ports, Shipping and Waterways",
    "Ministry of Power",
    "Ministry of Railways",
    "Ministry of Road Transport and Highways",
    "Ministry of Rural Development",
    "Ministry of Science and Technology",
    "Ministry of Skill Development and Entrepreneurship",
    "Ministry of Social Justice and Empowerment",
    "Ministry of Statistics and Programme Implementation",
    "Ministry of Steel",
    "Ministry of Textiles",
    "Ministry of Tourism",
    "Ministry of Tribal Affairs",
    "Ministry of Women and Child Development",
    "Ministry of Youth Affairs and Sports",
    # Departments that administer legislation in their own right
    "Department of Atomic Energy",
    "Department of Space",
    "Department of Telecommunications",
    "Department of Financial Services",
    "Department of Revenue",
    "Department of Economic Affairs",
    "Department of Expenditure",
    "Department of Higher Education",
    "Department of School Education and Literacy",
    "Department of Health Research",
    "Department of Pharmaceuticals",
    "Department of Food and Public Distribution",
)

# How much text to send the model. PRS "Highlights" open with the substance, and
# the ministry is almost always evident in the first screen of text -- a bigger
# window costs tokens and invites the model to latch onto a quoted agency name.
LLM_TEXT_CHARS = 6000
MIN_LLM_CONFIDENCE = 0.55
GROQ_MODEL = os.environ.get("VIDHANAI_GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_URL = os.environ.get("VIDHANAI_GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_USER_AGENT = os.environ.get(
    "VIDHANAI_GROQ_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
)

# "Ministry of X" / "Department of X" as written in legislative text, including
# dotted forms PRS uses for subordinate offices ("Ministry of Law and Justice").
_MINISTRY_RE = re.compile(
    r"\b(Ministry|Department) of ([A-Z][A-Za-z]*(?:[ ,&a-z-]+)?(?:[A-Z][A-Za-z]*)*)"
)

# Phrases that look like a ministry but are not the administering one
# (referrals, quotations, historical names, subordinate bodies).
_REJECT_FRAGMENTS = (
    "not below",
    "the bill",
    "bill,",
    "act,",
    "rules",
    "notification",
    "india observed",
    "writes",
    "stated",
    "said",
    "the committee",
    "committee",
    "amendment",
)


def _clean_candidate(raw: str) -> str:
    """Trim a regex capture to a plausible ministry name and fix casing."""
    cand = " ".join(raw.split())
    cand = cand.strip(" .,;:-")
    if not cand:
        return ""
    # Drop trailing clauses captured after the name ("... and Justice observed")
    for frag in _REJECT_FRAGMENTS:
        idx = cand.find(frag)
        if idx > 0:
            cand = cand[:idx].strip(" .,;:-")
    return cand


def _canonical(name: str) -> Optional[str]:
    """Map a spelled-out name onto the closed list, if it is close enough."""
    low = name.strip().lower()
    for km in UNION_MINISTRIES:
        k = km.lower()
        if low == k or k.startswith(low) or low.startswith(k):
            return km
    return None


def ministry_from_text(text: str, limit: int = 4000) -> Optional[dict]:
    """Return ``{ministry, confidence, evidence}`` derived from bill text.

    A quoted "Ministry of X" in the bill's own text is *evidence*, not a guess,
    so this is the highest-quality offline signal available. Names that appear
    only in the tail of the document (usually quoted agencies or citations) are
    not seen at all, and no name is invented that is not in the text.
    """
    if not text:
        return None
    head = text[:limit]
    # Aggregate by canonical name: count mentions and remember the first offset,
    # so a name repeated through the document outranks a one-off citation.
    seen: dict[str, dict] = {}
    for m in _MINISTRY_RE.finditer(head):
        cand = _clean_candidate(m.group(0))
        if not cand or len(cand) < 8:
            continue
        canonical = _canonical(cand) or cand
        entry = seen.setdefault(canonical, {"count": 0, "first": m.start(), "known": False})
        entry["count"] += 1
        entry["first"] = min(entry["first"], m.start())
        if canonical in UNION_MINISTRIES:
            entry["known"] = True
    if not seen:
        return None

    # Prefer names from the closed list; fall back to a literal quoted phrase.
    known = {name: e for name, e in seen.items() if e["known"]}
    pool = known or seen
    best = max(pool, key=lambda name: (pool[name]["count"], -pool[name]["first"]))
    entry = pool[best]
    if entry["count"] >= 2:
        confidence = 0.85
    else:
        confidence = 0.7 if entry["known"] else 0.55
    evidence_start = max(0, entry["first"] - 40)
    return {
        "ministry": best,
        "confidence": round(confidence, 2),
        "evidence": "quoted in bill text: "
        + " ".join(head[evidence_start:entry["first"] + len(best) + 20].split()),
    }


_NAME_STOPWORDS = {"of", "and", "the", "ministry", "department", "for", "&"}


def _tokens(name: str) -> set:
    return {
        t
        for t in re.split(r"[^a-z]+", name.lower())
        if t and t not in _NAME_STOPWORDS
    }


def canonical_from_short(value: str) -> Optional[str]:
    """Map PRS's short ministry label onto a full ministry name.

    PRS publishes a taxonomy label, not a full name -- the ministry field for the
    Bankers' Books Evidence Bill reads literally "Finance", and for the Public
    Examinations Bill "Personnel, Grievances and Pensions". Match by token
    coverage (so "Personnel, Grievances and Pensions" finds "Ministry of
    Personnel, Public Grievances and Pensions") and prefer the tightest fit.
    Returns ``None`` when nothing covers the label, in which case the caller
    keeps PRS's own wording rather than inventing a full name.
    """
    want = _tokens(value)
    if not want:
        return None
    best, best_key = None, None
    for name in UNION_MINISTRIES:
        have = _tokens(name)
        overlap = len(want & have)
        if not overlap:
            continue
        coverage = overlap / len(want)
        if coverage < 0.75:
            continue
        key = (round(coverage, 3), -len(have))
        if best_key is None or key > best_key:
            best, best_key = name, key
    return best


def ministry_from_prs(bill_url: str, timeout: int = 20) -> Optional[dict]:
    """Tier 1: the ministry PRS publishes on the bill page, if any.

    PRS's label is normalised to a full ministry name when it maps onto the
    closed list; the exact scraped string is always kept in ``evidence`` so the
    provenance of a normalised name is still checkable.
    """
    if not bill_url:
        return None
    try:
        import requests

        resp = requests.get(
            bill_url,
            timeout=timeout,
            headers={"User-Agent": GROQ_USER_AGENT},
        )
        resp.raise_for_status()
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.content, "html.parser")
        field = (
            soup.find("div", class_="field-name-field-ministry")
            or soup.find("div", class_="field-name-ministry")
            or soup.find("div", class_="views-field-field-ministry")
        )
        if not field:
            return None
        # The label ("Ministry:") shares the container, so read the field-items
        # child when present rather than the whole block.
        items = field.find("div", class_="field-items") or field
        value = " ".join(items.get_text(" ", strip=True).split())
        value = re.sub(r"^Ministry:?\s*", "", value, flags=re.I).strip()
        if not value or value.lower() in ("unknown", "n/a", "-", "not available"):
            return None
        ministry = canonical_from_short(value) or value
        return {
            "ministry": ministry,
            "confidence": 1.0,
            "evidence": f"scraped from PRS ministry field: {value!r} ({bill_url})",
        }
    except Exception as exc:  # pragma: no cover - network
        logger.warning("PRS ministry fetch failed for %s: %s", bill_url, exc)
    return None


def ministry_from_llm(title: str, text: str, api_key: Optional[str] = None) -> Optional[dict]:
    """Tier 3: ask Groq to choose from the closed list, with a rationale.

    Returns ``None`` on any failure, an ``Unknown`` answer, or a name that is
    neither in :data:`UNION_MINISTRIES` nor a literal "Ministry of X" quote from
    the text. The prompt asks for JSON so the answer is checkable rather than
    prose we would have to parse.
    """
    api_key = api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    candidates = "\n".join(f"- {m}" for m in UNION_MINISTRIES)
    snippet = (text or "")[:LLM_TEXT_CHARS]
    system = (
        "You identify which Union ministry of the Government of India administers an Indian "
        "parliamentary Bill. Choose the BEST match from the list below and reply with JSON only:\n"
        '{"ministry": "<exact name from the list, or \\"Unknown\\">", '
        '"confidence": <0-1>, "reason": "<one sentence>"}\n\n'
        "Rules: the ministry must come from the list verbatim. Do not invent a ministry, and do "
        'not answer "Unknown" unless the text gives no usable signal. Judge by the subject matter '
        "the Bill regulates, not by which ministry appears in a citation.\n\n"
        f"Allowed values:\n{candidates}"
    )
    user = f"Bill title: {title}\n\nBill text (PRS highlights):\n{snippet}"
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": GROQ_USER_AGENT,
        }
        body = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        # Same 429 tolerance as the summarizer: a burst of bills must not silently
        # downgrade to "no ministry" just because two calls landed back to back.
        import time as _time

        content = ""
        for attempt in range(3):
            resp = requests.post(GROQ_API_URL, json=body, headers=headers, timeout=180)
            if resp.status_code == 429:
                wait = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
                try:
                    wait = min(float(wait), 60.0) if wait else 5.0 * (2 ** attempt)
                except ValueError:
                    wait = 5.0 * (2 ** attempt)
                logger.warning("Groq rate limited during ministry inference; waiting %.0fs", wait)
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
            break
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(content)
    except Exception as exc:  # pragma: no cover - network/api
        logger.warning("LLM ministry inference failed for %r: %s", title[:60], exc)
        return None

    ministry = str(data.get("ministry") or "").strip()
    if not ministry or ministry.lower() == "unknown":
        return None
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < MIN_LLM_CONFIDENCE:
        return None
    # With only a title to go on the guess is materially weaker, so it is
    # discounted -- and the evidence says so, rather than hiding it.
    title_only = not snippet.strip()
    if title_only:
        confidence = min(confidence, 0.6)
        reason = f"inferred from the Bill title alone (no text available), model confidence {data.get('confidence')}"
    else:
        reason = str(data.get("reason") or "")[:300]
    # Guard 1: canonical list membership.
    canonical = next((m for m in UNION_MINISTRIES if m.lower() == ministry.lower()), None)
    if canonical:
        return {
            "ministry": canonical,
            "confidence": round(min(confidence, 0.9 if not title_only else 0.6), 2),
            "evidence": f"LLM ({GROQ_MODEL}) from closed list: {reason}",
        }
    # Guard 2: a literal "Ministry of X" the model copied out of the bill text.
    if ministry.lower() in snippet.lower() and ("ministry of" in ministry.lower() or "department of" in ministry.lower()):
        return {
            "ministry": ministry,
            "confidence": round(min(confidence, 0.75 if not title_only else 0.6), 2),
            "evidence": f"LLM ({GROQ_MODEL}) quoting bill text: {reason}",
        }
    logger.info("Rejected LLM ministry %r (not in list, not quoted) for %r", ministry, title[:60])
    return None


def resolve_ministry(bill: Bill, content_text: Optional[str] = None,
                     allow_llm: bool = True, allow_network: bool = True) -> Optional[dict]:
    """Run the tiers in order and return the first acceptable result.

    Returns ``{ministry, source, confidence, evidence}`` or ``None`` when every
    tier fails -- in which case the bill keeps whatever it had (usually
    ``Unknown``) rather than acquiring a fabricated value.
    """
    if (bill.ministry_source or "") == "prs" and bill.ministry and bill.ministry != "Unknown":
        return {
            "ministry": bill.ministry,
            "source": "prs",
            "confidence": bill.ministry_confidence or 1.0,
            "evidence": bill.ministry_evidence or f"scraped: {bill.url}",
        }

    if allow_network:
        found = ministry_from_prs(bill.url)
        if found:
            return {**found, "source": "prs"}

    text = content_text
    if text is None and bill.content is not None:
        text = bill.content.full_text or ""
    derived = ministry_from_text(text or "")
    if derived:
        return {**derived, "source": "bill_text"}

    if allow_llm:
        inferred = ministry_from_llm(bill.title, text or "")
        if inferred:
            return {**inferred, "source": "llm_inferred"}
    return None


def apply_resolution(bill: Bill, resolution: Optional[dict]) -> bool:
    """Write a resolution onto the Bill. Returns True when something changed.

    Refuses to overwrite a scraped ministry with a derived one.
    """
    if not resolution:
        return False
    if (bill.ministry_source or "") == "prs" and resolution["source"] != "prs":
        return False
    changed = (
        bill.ministry != resolution["ministry"]
        or (bill.ministry_source or "") != resolution["source"]
    )
    bill.ministry = resolution["ministry"]
    bill.ministry_source = resolution["source"]
    bill.ministry_confidence = resolution["confidence"]
    bill.ministry_evidence = resolution.get("evidence")
    return changed
