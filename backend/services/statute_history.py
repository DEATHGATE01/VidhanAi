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


def discover_parent_history(parent_title, parent_year, session, size=20, timeout=45):
    """Return (entries, note, source_url) for one parent statute.

    entries: [{title, year, act_number, handle, url}] — oldest first, deduplicated.
    The list may legitimately be empty (nothing catalogued, or the search failed);
    `note` always says which, so the UI never presents an empty history as a fact
    that no amendment exists.
    """
    key_words = [w for w in parent_key(parent_title, parent_year).split() if len(w) > 3]
    if not key_words:
        return [], "the parent statute's name has no distinctive words to search on", None
    query = " ".join(parent_key(parent_title, parent_year).split()[:8])
    url = f"https://indiacode.gov.in/search?query={query.replace(' ', '%20')}"

    try:
        resp = session.get(DISCOVER, params={"query": query, "size": size}, timeout=timeout)
    except Exception as exc:                      # network layer, any type
        return [], f"{SOURCE_LABEL} unreachable ({type(exc).__name__}); history not read", url
    if resp.status_code != 200:
        return [], f"{SOURCE_LABEL} returned HTTP {resp.status_code}; history not read", url
    try:
        payload = resp.json()
    except ValueError:
        return [], f"{SOURCE_LABEL} returned a non-JSON body; history not read", url

    objects = ((((payload.get("_embedded") or {}).get("searchResult") or {})
                .get("_embedded") or {}).get("objects")) or []
    seen = len(objects)
    entries, skipped, dropped = {}, 0, 0
    for obj in objects:
        ind = (obj.get("_embedded") or {}).get("indexableObject") or {}
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
        handle = ind.get("handle")
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
            if len(display_title) < len(existing.get("title") or ""):
                existing["title"] = display_title

    out = sorted(entries.values(), key=lambda e: (e["year"] or "9999", e["title"]))
    if not out:
        return [], (f"{SOURCE_LABEL}: searched \"{query}\" — {seen} records seen, none of them an "
                    f"amending Act or Ordinance for this statute ({skipped} unrelated, {dropped} untitled)"), url
    kept = ", ".join(f"{e['act_number'] or 'no number'} ({e['year'] or 'year not stated'})" for e in out)
    return out, (f"{SOURCE_LABEL}: {len(out)} amending instrument(s) catalogued against this statute — "
                 f"{kept} (from {seen} records, {skipped} unrelated or section-level records dropped)"), url
