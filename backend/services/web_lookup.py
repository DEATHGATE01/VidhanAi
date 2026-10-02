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
"""
from __future__ import annotations

import html
import re
import time
from datetime import datetime

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


def crawl_act(act, session: requests.Session) -> dict:
    """Run every reachable source for one Act. Returns findings + a trail.

    The trail is the point: it is what the UI shows instead of a bare "not found".
    """
    title = (act.title or "").replace("Act,", "Act,").strip()
    year = act.year or datetime.utcnow().year
    trail: list[dict] = []
    candidates: dict[int, list[str]] = {}   # act number -> [sources that claim it]

    def record(source, answer):
        trail.append({"source": source, "answer": answer,
                      "at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")})

    # 1. The Act's OWN document — authoritative. Search its text properly (it is
    #    the one place a Gazette header "(NO. X OF YYYY)" can be read directly),
    #    and say plainly when the PDF is still only the Bill text.
    own_text = None
    if getattr(act, "pdf_url", None):
        try:
            from services.act_dossier import fetch_act_text
            own_text, pdf_note = fetch_act_text(act, session)
        except Exception as exc:
            own_text, pdf_note = None, f"read failed ({type(exc).__name__})"
        if own_text:
            nums = find_act_number_in(own_text, year)
            bill_no = re.search(r"\bBill\s+No\.?\s*([0-9A-Za-z\-]+)\s+of\s+(\d{4})", own_text, re.I)
            for n in nums:
                candidates.setdefault(n, []).append("PRS India (Act PDF)")
            if nums:
                record("PRS India (the Act's own PDF)",
                       f"text read; carries the Gazette header for {['No. %d of %d' % (n, year) for n in nums]}")
            elif bill_no:
                record("PRS India (the Act's own PDF)",
                       f"text read; it is still the Bill text (Bill No. {bill_no.group(1)} of "
                       f"{bill_no.group(2)}) and contains no Act number")
            else:
                record("PRS India (the Act's own PDF)",
                       "text read; no Act number and no Bill number in the text")
        else:
            record("PRS India (the Act's own PDF)", pdf_note or "not retrievable")
    else:
        record("PRS India (the Act's own PDF)", "no pdf_url on the act row")

    # 2. Wikipedia (unwalled API).
    wiki_url, wiki_text, wiki_note = wikipedia_lookup(title, year, session)
    if wiki_text:
        nums = find_act_number_in(wiki_text, year)
        for n in nums:
            candidates.setdefault(n, []).append("Wikipedia")
        record("Wikipedia", (f"article found; claims {['No. %d of %d' % (n, year) for n in nums]}"
                             if nums else "article found, no Act number"))
    else:
        record("Wikipedia", wiki_note)

    # 3. India Code — authoritative, and re-checked every run because its ingestion
    #    lags assent. Reuses the proven matcher (exact title + year + CENTRAL only).
    try:
        from scripts.maintenance.enrich_indiacode import discover_india_code_record
        rec, why = discover_india_code_record(session, title, year)
        if rec:
            num = rec.get("act_number") if isinstance(rec, dict) else None
            if num:
                candidates.setdefault(int(num), []).append("India Code")
            record("India Code", f"record found; Act No. {num}"
                                 if num else "record found; no Act number field")
        else:
            record("India Code", f"no {year} record — {str(why)[:110]}")
    except Exception as exc:
        record("India Code", f"check failed ({type(exc).__name__})")

    # 4. eGazette — the body that assigns numbers. Session-gated ASP.NET, and its
    #    TLS refuses scripted clients while serving real browsers, so this records
    #    the attempt honestly instead of pretending the source was checked.
    try:
        r = session.get("https://egazette.gov.in/RecentUploads.aspx",
                        params={"Category": 1}, timeout=40)
        ok, reason = _looks_like_the_page(r.text, r.url)
        record("eGazette (assigns Act numbers)",
               "reachable; search is a session-scoped postback — number not retrievable unattended"
               if r.status_code == 200 else f"HTTP {r.status_code}, {reason}")
    except Exception as exc:
        record("eGazette (assigns Act numbers)",
               f"refuses scripted clients ({type(exc).__name__}) — reachable only in a real "
               f"browser session; number not retrievable unattended")

    # 5. Note the engines we must NOT use, so the trail is not misleading.
    record("Google / Bing / DuckDuckGo / Mojeek",
           "bot-walled from this host (captcha or JS-only results); not used as fact sources")

    agreed = {n: srcs for n, srcs in candidates.items() if len(set(srcs)) >= 2}
    return {
        "candidates": candidates,
        "corroborated_number": (sorted(agreed)[0] if agreed else None),
        "corroborated_by": agreed,
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
