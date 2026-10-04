"""Discover a parent statute's amendment history from India Code's own catalogue.

WHY: an Act page can show the bill that produced that Act, but a statute's history
is longer than the Act — the Andhra Pradesh Reorganisation Act, 2014 was amended in
2014 (No. 19), in 2015 (No. 12) and again in 2026. Those earlier chapters are facts
held by India Code, and they are reachable through its public search API.

WHAT THIS DOES: given a parent statute (title + year, as read from the amending
Act's own text), asks India Code's DSpace search for records naming that statute and
keeps only the ones that are LEGISLATION (a title containing Act/Ordinance/Order and
a year), which is what an amendment to that statute looks like. Section-level records
India Code also returns ("Expert Committee for setting up of a capital ...") are
dropped: they are parts of the parent, not chapters of its history.

HONESTY: nothing here is inferred. Every entry comes from an India Code record and
carries the handle it was read from, so the UI can link each one. If the search
returns nothing usable, the note says so and the caller shows that instead of a
timeline. Records are never padded out to look like a complete history — the note
records the query and how many records were kept out of how many seen.
"""
from __future__ import annotations

import re

from services.act_dossier import looks_interleaved as looks_damaged_name

DISCOVER = "https://indiacode.gov.in/server/api/discover/search/objects"
SOURCE_LABEL = "India Code (indiacode.gov.in)"
ITEM_BASE = "https://indiacode.gov.in/handle/"
# India Code serves its catalogue to a plain client; identify the project honestly.
USER_AGENT_FALLBACK = "VidhanAI/1.0 (academic legislative-tracking project)"

# A chapter of a statute's history is legislation: it has a title ending in Act /
# Ordinance / Order / Regulation and a year. Anything else India Code returns for the
# same search (a section name, a notification fragment) is not an amendment.
_RE_LEGISLATION = re.compile(r"\b(Act|Adhiniyam|Ordinance|Order|Regulation)\b", re.I)
# A chapter of the history is an instrument that CHANGES the statute.
_RE_AMENDING = re.compile(r"\b(Amendment|Ordinance|Repeal|Removal of Difficulties)\b", re.I)
# Not legislation: notifications reproducing the parent's text ("In exercise of the
# powers conferred by Section 101 ..."), and "Rules" — subordinate legislation made
# UNDER the statute, which is a different thing from the statute being amended.
_RE_NOT_LEGISLATION = re.compile(r"^\s*(in exercise of|notification|order\b)|\bRules\b", re.I)
_RE_ACT_NO_IN_TITLE = re.compile(r"\b(\d{1,3})\s+of\s+((?:1[89]|20)\d\d)\b")
# India Code appends the instrument's fate to its title: "... Act, 2015, 12 of 2015,
# (Rep., Act 31 of 2019)" means Act 12 of 2015 was REPEALED by Act 31 of 2019. That is
# part of the statute's history, so it is recorded rather than stripped away.
_RE_REPEALED_BY = re.compile(r"\(\s*Rep\.?,?\s*(?:Act\s*)?(\d{1,3})\s+of\s+((?:1[89]|20)\d\d)\s*\)", re.I)
_RE_YEAR_ONLY = re.compile(r"\b((?:1[89]|20)\d\d)\b")

_STOPWORDS = {"the", "act", "of", "and", "a", "an"}


def parent_key(title: str, year) -> str:
    """Stable key for a parent statute: its distinctive words, without year.

    'Andhra Pradesh Reorganisation Act' + 2014 -> 'andhra pradesh reorganisation'.
    Used to group the same parent across Acts and to store its history once.
    """
    words = [w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if w not in _STOPWORDS]
    return " ".join(words)


def _norm_title(title: str) -> str:
    """Title normalised for comparison: no leading article, no punctuation, lowercase."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"^\s*the\s+", "", (title or "").lower(), flags=re.I))


def _metadata_value(ind, *keys):
    md = ind.get("metadata") or {}
    for key in keys:
        vals = md.get(key) or []
        if vals:
            return vals[0].get("value")
    return None


def _fetch_all_pages(session, query, size=50, max_pages=10, timeout=45):
    """Read EVERY page of a catalogue query, not just the first.

    India Code paginates its results, so the old single request saw only the first 50
    records for a statute's name and silently truncated rich histories (the RBI Act
    showed 4 of its 15+ chapters). This walks the pages until the reported total is
    reached — or until max_pages, which is reported back as `truncated` so the caller
    can say the list may be incomplete instead of implying it is complete.

    Returns (records, info) where info = {seen, total, pages, total_pages, truncated}.
    """
    records, page, info = [], 0, {"seen": 0, "total": None, "pages": 0, "total_pages": None,
                                  "truncated": False}
    while page < max_pages:
        try:
            resp = session.get(DISCOVER, params={"query": query, "size": size, "page": page},
                               timeout=timeout)
        except Exception:
            info["truncated"] = True
            break
        if resp.status_code != 200:
            info["truncated"] = True
            break
        try:
            payload = resp.json()
        except ValueError:
            info["truncated"] = True
            break
        result = (payload.get("_embedded") or {}).get("searchResult") or {}
        page_info = result.get("page") or {}
        objects = ((result.get("_embedded") or {}).get("objects")) or []
        if not objects:
            break
        info["total"] = page_info.get("totalElements", info["total"])
        info["total_pages"] = page_info.get("totalPages", info["total_pages"])
        info["pages"] += 1
        records.extend(obj.get("_embedded", {}).get("indexableObject") or {} for obj in objects)
        info["seen"] = len(records)
        if info["total"] and len(records) >= info["total"]:
            break
        page += 1
    if info["total_pages"] and info["pages"] < info["total_pages"]:
        info["truncated"] = True
    return records, info


def discover_parent_history(parent_title, parent_year, session, size=50, max_pages=10, timeout=45):
    """Return (entries, note, source_url) for one parent statute.

    entries: [{title, year, act_number, repealed_by, is_parent, handle, url}] — oldest
    first, deduplicated. The list may legitimately be empty (nothing catalogued, or the
    search failed); `note` always says which, so the UI never presents an empty history
    as a fact that no amendment exists.
    """
    if looks_damaged_name(parent_title):
        # The name was spliced by the PDF's text layer ("InsurAance Act"). Searching on it
        # returns other statutes entirely, so the search is not run at all and the caller
        # gets that reason rather than a chain built from a wrong query.
        return [], (f"the parent statute's name is unreadable in the source PDF's text layer "
                    f"(\"{parent_title}\", {parent_year}) — the catalogue search needs a real "
                    f"name and is not run on a spliced one"), None
    key_words = [w for w in parent_key(parent_title, parent_year).split() if len(w) > 3]
    if not key_words:
        return [], "the parent statute's name has no distinctive words to search on", None
    query = " ".join(parent_key(parent_title, parent_year).split()[:8])
    url = f"https://indiacode.gov.in/search?query={query.replace(' ', '%20')}"

    # Read every page of the result set: a single request truncates rich histories.
    records, info = _fetch_all_pages(session, query, size=size, max_pages=max_pages, timeout=timeout)
    if not records:
        reason = ("the query failed or timed out" if info.get("truncated")
                  else "nothing is catalogued under that name")
        return [], f"{SOURCE_LABEL}: searched \"{query}\" — {reason}", url
    seen = info["seen"]
    entries, skipped, dropped, predated = {}, 0, 0, 0
    for ind in records:
        title = (_metadata_value(ind, "dc.title") or "").strip()
        if not title:
            dropped += 1
            continue
        low = title.lower()
        # Must actually name this statute...
        if not all(w in low for w in key_words):
            skipped += 1
            continue
        # ...be legislation, not one of the parent's own sections or a notification...
        if not _RE_LEGISLATION.search(title) or _RE_NOT_LEGISLATION.search(title):
            skipped += 1
            continue
        # ...and be either the parent itself (the root of the chain) or an instrument
        # that changes it. A bare section name is neither.
        is_parent = _norm_title(title) == _norm_title(parent_title)
        if not is_parent and not _RE_AMENDING.search(title):
            skipped += 1
            continue
        year = _metadata_value(ind, "dc.date.issued", "dc.year") or ""
        m = _RE_ACT_NO_IN_TITLE.search(title)
        if m:
            act_number, year_from_title = f"{m.group(1)} of {m.group(2)}", m.group(2)
        else:
            act_number, year_from_title = None, None
        rep = _RE_REPEALED_BY.search(title)
        repealed_by = f"{rep.group(1)} of {rep.group(2)}" if rep else None
        ym = _RE_YEAR_ONLY.search(str(year)) or (_RE_YEAR_ONLY.search(title) if not year else None)
        resolved_year = year_from_title or (ym.group(1) if ym else None) or (str(year)[:4] or None)
        # An instrument dated BEFORE the statute cannot amend it. Those records are other
        # statutes that merely share words with the name — a "Railways (Amendment) Act,
        # 1961" under the Railways Act, 1989, or a 1993 record surfacing under a 2024 Act.
        try:
            if parent_year and resolved_year and int(str(resolved_year)[:4]) < int(str(parent_year)[:4]):
                predated += 1
                continue
        except (TypeError, ValueError):
            pass
        handle = ind.get("handle")
        # India Code labels each record with what it is — ACT, ORDINANCE, ORDER,
        # NOTIFICATION, or one of the parent's parts (SECTION/SCHEDULE/RULE). Keeping the
        # label lets the UI name the instrument instead of guessing from the title.
        instrument = (_metadata_value(ind, "dc.identifier.collection") or "").strip() or None
        # India Code often holds the same instrument twice — once plain and once with its
        # number and fate appended ("...Act, 2015" vs "...Act, 2015, 12 of 2015, (Rep., Act
        # 31 of 2019)"). Both the number and the repeal are shown as their own fields, so
        # the title displayed is the plain one; the appended form is only a key.
        base = re.sub(r"[,\s]+(?:\(\s*Rep\.?,?\s*(?:Act\s*)?)?\d{1,3}\s+of\s+(?:1[89]|20)\d\d\s*\)?\s*$",
                      "", title, flags=re.I)
        base = re.sub(r"[,\s]+(?:Rep\.?,?\s*(?:Act\s*)?)?\d{1,3}\s+of\s+(?:1[89]|20)\d\d\s*\)?\s*,?\s*$",
                      "", base, flags=re.I)
        display_title = base if len(base) >= 20 else title
        dkey = (_norm_title(base), resolved_year)
        existing = entries.get(dkey)
        if existing is None:
            entries[dkey] = {
                "title": display_title,
                "year": resolved_year,
                "act_number": act_number,
                "repealed_by": repealed_by,
                "instrument": instrument,
                "is_parent": is_parent,
                "handle": handle,
                "url": (ITEM_BASE + handle) if handle else url,
            }
        else:
            # Merge the two copies without losing a fact: the plain one usually carries the
            # cleaner title, the annotated one the number and the repeal.
            if act_number and not existing.get("act_number"):
                existing["act_number"] = act_number
            if repealed_by and not existing.get("repealed_by"):
                existing["repealed_by"] = repealed_by
            if instrument and not existing.get("instrument"):
                existing["instrument"] = instrument
            if len(display_title) < len(existing.get("title") or ""):
                existing["title"] = display_title

    out = sorted(entries.values(), key=lambda e: (e["year"] or "9999", e["title"]))
    detail = (f"{seen} records read over {info['pages']} "
              f"page{'' if info['pages'] == 1 else 's'}, {skipped} unrelated or section-level, "
              f"{predated} predating the statute, {dropped} untitled")
    if info.get("truncated"):
        detail += ("; the result set was larger than this read, so the list may be incomplete")
    if not out:
        return [], (f"{SOURCE_LABEL}: searched \"{query}\" — {detail}; none of them an amending "
                    f"Act or Ordinance for this statute"), url
    kept = ", ".join(f"{e['act_number'] or 'no number'} ({e['year'] or 'year not stated'})" for e in out)
    return out, (f"{SOURCE_LABEL}: {len(out)} amending instrument(s) catalogued against this "
                 f"statute — {kept} ({detail})."), url
