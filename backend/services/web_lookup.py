"""Look facts up on the open web when PRS does not publish them.

WHY THIS EXISTS
The Act page said "Not found — sources checked" for the Act number and in-force
status of every 2026 Act. That phrasing is only honest if something actually
searched. This module does the searching, records WHAT was checked and what each
source answered, and returns a value only when it can be corroborated.

WHAT IS REACHABLE FROM HERE (measured, not assumed)
  - PRS India        : reachable, but publishes ONLY a per-Act PDF. Its Acts list
                       has a Title and a Year column and no Act number at all, and
                       there is no per-Act detail page. So PRS is authoritative for
                       assent + the Act's text, and silent on numbers by design.
  - India Code       : reachable and authoritative, but has NOT ingested any 2026
                       Act yet (verified against its DSpace search).
  - Wikipedia API    : reachable, unwalled.
  - eGazette         : the body that ASSIGNS Act numbers, reachable but the search
                       is a session-scoped ASP.NET postback; attempted and recorded.
  - Google/Bing/Mojeek/DuckDuckGo/Startpage: all bot-walled from this machine
    (captcha or JS-only SERP), so they are NOT used as fact sources.
That set is what the trail reports. If a source later knows the number, a re-run
fills it in with no code change.

HONESTY CONTRACT (mirrors blocked-page-recovery)
  - A fetch is only believed if the body looks like the requested page: the skill's
    "fake successes" (Google Cache stubs, AMP redirect stubs, multi-KB rate-limit
    bodies, interstitial titles) are rejected by _looks_like_the_page.
  - Archive copies carry their snapshot date as provenance, never passed off as live.
  - Nothing is guessed: a number is written only when two independent sources agree,
    or when the Act's OWN document carries the Gazette header "(NO. X OF YYYY)".
  - A DERIVED value is labelled as derived. When no source states the in-force
    status, it is derived from the Act's own assent date and stored with the reason
    in `acts.status_basis`, so the UI can show "in force" without implying that a
    source said so.

EXTENDING IT (news, sentiment, ...)
Sources live in the SOURCES registry below. A new source is a function
`fn(act, session, ctx) -> {"answer": "<trail line>"}` plus one LookupSource entry,
tagged with `kinds` so a later pass can select it (`sources_for(("news",))`). The
trail, storage, corroboration and UI are shared — a source only reads one site.
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

# Titles that mean "this is not the page you asked for".
_INTERSTITIAL = re.compile(
    r"(just a moment|attention required|access denied|are you a robot|"
    r"complete the following challenge|unusual traffic|enable javascript|"
    r"<title>\s*(redirecting|google search)\s*</title>)", re.I)
_MIN_BODY = 500

# "(NO. 12 OF 2023)" is the Gazette's own header; "No. 12 of 2023" appears in
# news, India Code and Wikipedia prose.
_RE_ACT_NO = re.compile(r"\(?\s*NO\.?\s*(\d{1,3})\s+OF\s+(20\d\d)\s*\)?", re.I)
_RE_REPEALED = re.compile(r"\b(repealed|repeal(?:s|ed)? by|no longer in force)\b", re.I)


def _looks_like_the_page(body: str, url: str) -> tuple[bool, str]:
    """Reject the known fake successes. Returns (ok, reason)."""
    if not body or len(body) < _MIN_BODY:
        return False, f"body too small ({len(body)} bytes)"
    m = _INTERSTITIAL.search(body[:4000])
    if m:
        return False, f"interstitial detected ('{m.group(0)[:40]}')"
    if re.search(r'<meta[^>]+http-equiv=["\']?refresh', body[:2000], re.I) and url.split("//")[-1][:25] in body[:2000]:
        return False, "meta-refresh stub pointing back at the original"
    return True, "ok"


def live_fetch(url: str, session: requests.Session, timeout: int = 45):
    """Direct fetch. Returns (text|None, provenance, note)."""
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        return None, None, f"live fetch failed ({type(exc).__name__})"
    ok, reason = _looks_like_the_page(r.text, url)
    if r.status_code != 200 or not ok:
        return None, None, f"live fetch HTTP {r.status_code}, {reason}"
    return r.text, "live", "ok"


def wayback_fetch(url: str, session: requests.Session, timeout: int = 45):
    """Archive fallback. Returns (text|None, provenance, note) with snapshot date."""
    try:
        meta = session.get("https://archive.org/wayback/available",
                           params={"url": url}, timeout=timeout).json()
        snap = (meta.get("archived_snapshots") or {}).get("closest") or {}
        if not snap.get("url"):
            return None, None, "no Wayback snapshot"
        r = session.get(snap["url"], timeout=timeout)
        ok, reason = _looks_like_the_page(r.text, url)
        if not ok:
            return None, None, f"snapshot unusable ({reason})"
        return r.text, f"snapshot {snap.get('timestamp', '')[:8]}", "ok"
    except Exception as exc:
        return None, None, f"wayback failed ({type(exc).__name__})"


def fetch_with_ladder(url: str, session: requests.Session):
    """Live first, then the archive — cheapest first, provenance preserved."""
    text, prov, note = live_fetch(url, session)
    if text:
        return text, prov, note
    a_text, a_prov, a_note = wayback_fetch(url, session)
    if a_text:
        return a_text, a_prov, a_note
    return None, None, f"{note}; {a_note}"


def _plain(body: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def wikipedia_lookup(title: str, year: int, session: requests.Session):
    """The one unwalled search API here. Returns (url|None, text|None, note)."""
    try:
        r = session.get("https://en.wikipedia.org/w/api.php",
                        params={"action": "query", "list": "search",
                                "srsearch": f'"{title}" {year}', "format": "json"},
                        timeout=30)
        hits = ((r.json().get("query") or {}).get("search") or [])
    except Exception as exc:
        return None, None, f"wikipedia API failed ({type(exc).__name__})"
    if not hits:
        return None, None, "wikipedia: no article"
    page = hits[0]["title"]
    try:
        url = f"https://en.wikipedia.org/wiki/{page.replace(' ', '_')}"
        body = session.get(url, timeout=30).text
        return url, _plain(body), f"wikipedia article '{page}'"
    except Exception as exc:
        return None, None, f"wikipedia fetch failed ({type(exc).__name__})"


def find_act_number_in(text: str, year: int):
    """Pull every 'No. X of <year>' claim out of a body."""
    if not text:
        return []
    found = []
    for num, yr in _RE_ACT_NO.findall(text):
        if int(yr) == int(year):
            found.append(int(num))
    return found


# ---------------------------------------------------------------------------
# Source registry
#
# Each entry is one place the crawler can look. Adding a source is meant to be a
# drop-in: write a function `fn(act, session, ctx) -> dict` that reads its own site,
# writes findings into `ctx` ("answer" is the trail line it reports under), then
# append a LookupSource to SOURCES below. The trail formatting, the storage on the
# Act, the corroboration rule and the Act-page UI are all shared, so a new source
# only has to know how to read one site.
#
# FOR THE FUTURE news / sentiment work: give the new source `kinds=("news",)` (or
# ("sentiment",)) and select it with `sources_for(("news",))`. A pass then collects
# only the sources it wants; nothing else about the machinery changes.
# ---------------------------------------------------------------------------
@dataclass
class LookupSource:
    """One lookup route: a label, a function, and what it is useful for."""

    name: str
    run: Callable[..., dict]
    kinds: tuple = ("act_identity", "bill_number", "status")


def sources_for(kinds) -> list:
    """Sources serving any of `kinds` (default: every registered source)."""
    wanted = set(kinds) if kinds else None
    return [s for s in SOURCES if wanted is None or (set(s.kinds) & wanted)]


def _src_act_pdf(act, session, ctx) -> dict:
    """The Act's own document: authoritative, and the only place the Gazette
    header '(NO. X OF YYYY)' can be read directly. Also yields the Bill number."""
    if not getattr(act, "pdf_url", None):
        return {"answer": "no pdf_url on the act row"}
    try:
        from services.act_dossier import fetch_act_text
        text, note = fetch_act_text(act, session)
    except Exception as exc:
        return {"answer": f"read failed ({type(exc).__name__})"}
    if not text:
        return {"answer": note or "not retrievable"}

    nums = find_act_number_in(text, ctx["year"])
    for n in nums:
        ctx["candidates"].setdefault(n, []).append("PRS India (Act PDF)")

    from services.act_dossier import extract_bill_number
    bill_number = extract_bill_number(text)
    if bill_number:
        ctx["bill_number"] = bill_number

    if nums:
        return {"answer": "text read; carries the Gazette header for "
                          f"{['No. %d of %d' % (n, ctx['year']) for n in nums]}"}
    if bill_number:
        return {"answer": f"text read; it is still the Bill text (Bill No. "
                          f"{bill_number}) and contains no Act number"}
    return {"answer": "text read; no Act number and no Bill number in the text"}


def _src_wikipedia(act, session, ctx) -> dict:
    _url, text, note = wikipedia_lookup(ctx["title"], ctx["year"], session)
    if not text:
        return {"answer": note}
    nums = find_act_number_in(text, ctx["year"])
    for n in nums:
        ctx["candidates"].setdefault(n, []).append("Wikipedia")
    if nums:
        return {"answer": f"article found; claims "
                          f"{['No. %d of %d' % (n, ctx['year']) for n in nums]}"}
    return {"answer": "article found, no Act number"}


def _src_india_code(act, session, ctx) -> dict:
    """Authoritative, and re-checked every run because its ingestion lags assent."""
    try:
        from scripts.maintenance.enrich_indiacode import discover_india_code_record
        rec, why = discover_india_code_record(session, ctx["title"], ctx["year"])
    except Exception as exc:
        return {"answer": f"check failed ({type(exc).__name__})"}
    if not rec:
        return {"answer": f"no {ctx['year']} record — {str(why)[:110]}"}
    ctx["india_code_record"] = rec
    num = rec.get("act_number") if isinstance(rec, dict) else None
    if num:
        ctx["candidates"].setdefault(int(num), []).append("India Code")
        return {"answer": f"record found; Act No. {num}"}
    return {"answer": "record found; no Act number field"}


def _src_egazette(act, session, ctx) -> dict:
    """The body that assigns Act numbers. Session-gated ASP.NET whose TLS refuses
    scripted clients while serving real browsers — recorded honestly rather than
    pretending the source was checked."""
    try:
        r = session.get("https://egazette.gov.in/RecentUploads.aspx",
                        params={"Category": 1}, timeout=40)
        ok, reason = _looks_like_the_page(r.text, r.url)
        if r.status_code == 200:
            return {"answer": "reachable; search is a session-scoped postback — "
                              "number not retrievable unattended"}
        return {"answer": f"HTTP {r.status_code}, {reason}"}
    except Exception as exc:
        return {"answer": f"refuses scripted clients ({type(exc).__name__}) — reachable "
                          f"only in a real browser session; number not retrievable unattended"}


def _src_open_engines(act, session, ctx) -> dict:
    """A note, not a source: the engines we must NOT use, so the trail is not
    misleading about what was searched."""
    return {"answer": "bot-walled from this host (captcha or JS-only results); "
                      "not used as fact sources"}


SOURCES: list = [
    LookupSource("PRS India (the Act's own PDF)", _src_act_pdf),
    LookupSource("Wikipedia", _src_wikipedia),
    LookupSource("India Code", _src_india_code),
    LookupSource("eGazette (assigns Act numbers)", _src_egazette),
    LookupSource("Google / Bing / DuckDuckGo / Mojeek", _src_open_engines),
]


def crawl_act(act, session: requests.Session, kinds=("act_identity", "bill_number", "status")) -> dict:
    """Run every relevant source for one Act. Returns findings + a trail.

    The trail is the point: it is what the UI shows instead of a bare "not found".
    """
    ctx = {
        "title": (act.title or "").strip(),
        "year": act.year or datetime.utcnow().year,
        "candidates": {},        # act number -> [sources claiming it]
        "bill_number": None,
        "india_code_record": None,
    }
    trail: list[dict] = []

    for source in sources_for(kinds):
        try:
            out = source.run(act, session, ctx)
            answer = out.get("answer") if isinstance(out, dict) else str(out)
        except Exception as exc:  # a source must never take the pass down
            answer = f"check failed ({type(exc).__name__})"
        trail.append({"source": source.name, "answer": answer,
                      "at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")})

    agreed = {n: srcs for n, srcs in ctx["candidates"].items() if len(set(srcs)) >= 2}

    derived_status = status_basis = None
    if "status" in kinds:
        from services.act_dossier import derive_status
        derived_status, status_basis = derive_status(act)
        if derived_status:
            trail.append({"source": "Status (derived, labelled)",
                          "answer": status_basis,
                          "at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")})

    return {
        "candidates": ctx["candidates"],
        "corroborated_number": (sorted(agreed)[0] if agreed else None),
        "corroborated_by": agreed,
        "bill_number": ctx["bill_number"],
        "derived_status": derived_status,
        "status_basis": status_basis,
        "trail": trail,
    }


def format_trail(result: dict, checked_at: str | None = None) -> str:
    """One-line-per-source summary stored on the Act and shown in the UI."""
    stamp = checked_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"Web lookup {stamp} — sources checked:"]
    for item in result["trail"]:
        lines.append(f"  · {item['source']}: {item['answer']}")
    if result["corroborated_number"]:
        srcs = ", ".join(sorted(set(sum(result["corroborated_by"].values(), []))))
        lines.append(f"  => Act number No. {result['corroborated_number']} "
                     f"corroborated by {srcs}")
    else:
        lines.append("  => no Act number corroborated by any reachable source")
    return "\n".join(lines)
