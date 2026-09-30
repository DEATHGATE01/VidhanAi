"""Enrich Acts with Act Number and assent date sourced from India Code.

Usage (run from `backend/` or anywhere -- paths are resolved from this file):

    python scripts/maintenance/enrich_indiacode.py --limit 8 --delay 1.0
    python scripts/maintenance/enrich_indiacode.py --act-ids 11,14   # a few acts
    python scripts/maintenance/enrich_indiacode.py --dry-run         # print, write nothing

The honest contract, verbatim from the charter (docs/CTO_ACTS.md): a field you
cannot source stays NULL, and the report says why. Concretely:

- Source: the DSpace REST API of indiacode.gov.in -- the migrated host of
  indiacode.nic.in, which 302-redirects there (verified 2026-09-30: HTTP 302
  on nic.in in ~0.4 s; HTTP 200 in ~1 s on /server/api/discover/search/objects;
  HTTP 200 on /server/api/core/items/<uuid>). Only values literally present in
  that API's response are written; anything else stays NULL. Nothing is
  invented, and no filename regex is used as a fallback.
- Match is exact on THREE keys at once (verified 2026-09-30: relaxing any one
  of them attaches a wrong record's number):
    1. ``dc.identifier.state_name == 'CENTRAL'`` -- search hits include state
       adoptions of the same Act name (a query for "industrial relations code
       amendment act" returns the Uttar Pradesh adoption, not the central Act);
    2. ``dc.title`` equals the act's normalized PRS title -- hits include
       amendment notifications, amended parent acts, and unrelated acts (a
       query for "jan vishwas amendment of provisions act" returns "The Legal
       Metrology Act, 2009" and "The Indian Forest Act, 1927" hits, none of
       which is the Jan Vishwas Act itself);
    3. ``dc.date.act_year`` equals the act's year from the PRS PDF path --
       services.act_linker.normalize() strips the year, so a year-blind title
       match could attach e.g. the 1923 Bihar Boilers Act's number to the 2025
       central one.
  An act with no hit matching all three keeps NULL -- never a guess.
- ``dc.identifier.act_name`` (matched on by an earlier draft of this script)
  does NOT exist on central records -- they carry ``dc.title`` only -- so an
  act_name-keyed match would never fire. This draft keys on ``dc.title``.
- Assent date: only ``dc.date.enact_date`` is ever written to ``assent_date``
  (e.g. 2025-04-04 for The Boilers Act, 2025, which is >= that act's last PRS
  event date 2025-04-03 -- consistent with assent following passage).
  ``dc.date.issued`` equals ``enact_date`` on the records inspected but is not
  pinned to the Assented-to-on semantics, so it is not used. Acts without a
  parseable ``dc.date.enact_date`` keep a NULL assent_date.
- ``source`` flips to 'indiacode' only for enriched acts and ``source_url``
  points at the exact API item record. sync_acts.py never clobbers an enriched
  row's source/source_url (it refreshes PRS listing fields only, and keeps
  'indiacode' provenance even when the PRS listing row changes).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

import requests

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from services.act_linker import normalize  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://indiacode.gov.in"
DISCOVER = BASE + "/server/api/discover/search/objects"


def parse_args():
    p = argparse.ArgumentParser(description="Source Act Number and assent date from India Code with provenance.")
    p.add_argument("--limit", type=int, default=None, help="max acts to process")
    p.add_argument("--act-ids", type=str, default=None, help="comma-separated Act.id values")
    p.add_argument("--dry-run", action="store_true", help="print results, write nothing")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between network calls")
    p.add_argument("--refresh", action="store_true",
                   help="also revisit acts whose act_number is already sourced")
    return p.parse_args()


def _first(md, key):
    """First value of a DSpace metadata field, or None."""
    values = md.get(key) or []
    return values[0].get("value") if values else None


def discover_india_code_record(session, act_title: str, act_year):
    """Query India Code and return (record, item_url) for an exact match.

    A hit must match ALL THREE keys (state CENTRAL + exact dc.title + exact
    act_year); anything else is a different Act's record and is never returned.
    Returns (None, reason) when nothing matches -- a fuzzy hit is a different
    Act's number and is never returned.
    """
    query = " ".join(normalize(act_title).split()[:12]).strip()
    if not query:
        return None, "empty normalized title"
    try:
        resp = session.get(DISCOVER, params={"query": query, "size": 10}, timeout=30)
    except requests.RequestException as exc:
        return None, f"indiacode.gov.in unreachable: {exc}"
    if resp.status_code != 200:
        return None, f"indiacode.gov.in HTTP {resp.status_code}"
    try:
        payload = resp.json()
    except ValueError:
        return None, "indiacode.gov.in returned non-JSON body"
    objects = (payload.get("_embedded", {}).get("searchResult", {})
               .get("_embedded", {}).get("objects", []))
    want = normalize(act_title)
    for obj in objects:
        idx_obj = obj.get("_embedded", {}).get("indexableObject", {})
        md = idx_obj.get("metadata", {})
        # Key 1: central Acts only (state adoptions share the same Act names).
        if (_first(md, "dc.identifier.state_name") or "").strip().upper() != "CENTRAL":
            continue
        # Key 2: exact normalized title (dc.title; dc.identifier.act_name does
        # not exist on central records).
        ic_title = _first(md, "dc.title")
        if not ic_title or normalize(ic_title) != want:
            continue
        # Key 3: exact Act year (normalize() strips the year, so the title
        # match alone cannot tell the 1923 state Boilers Act from the 2025 one).
        ic_year = (_first(md, "dc.date.act_year") or "").strip()
        if str(act_year or "") != ic_year:
            continue
        # Provenance URL for the matched record. The canonical link lives on the
        # OUTER search object (_links.indexableObject.href ->
        # /server/api/core/items/<uuid>), not on the embedded object, so reading
        # _links off idx_obj found nothing and every act silently stored the bare
        # host -- which is not provenance anyone can check. Prefer the API item
        # URL, then the human handle URL, and only fall back to the host.
        uuid = idx_obj.get("uuid")
        handle = (idx_obj.get("handle") or "").strip()
        item_url = (((obj.get("_links") or {}).get("indexableObject") or {}).get("href")
                    or (BASE + "/server/api/core/items/" + uuid if uuid else None)
                    or (BASE + "/handle/" + handle if handle else None)
                    or BASE + "/")
        return {"metadata": md, "item_url": item_url}, item_url
    return None, f"no exact CENTRAL/title/year match among {len(objects)} hit(s)"


def enrich_act(session, act):
    """Return (fields_or_None, reason) with India Code values for one Act.

    fields carries only values literally present in the API response:
    {'act_number': str, 'assent_date': datetime|None, 'item_url': str,
     'evidence': str}. A missing act_number means no usable match --
    assent_date is then never written either (a number-less record is not
    this Act's).
    """
    record, item_url = discover_india_code_record(session, act.title, act.year)
    if record is None:
        return None, item_url  # item_url carries the reason here
    md = record["metadata"]
    number = _first(md, "dc.identifier.act_number")
    if not number:
        return None, "exact match has no dc.identifier.act_number"
    fields = {
        "act_number": str(number),
        "item_url": item_url,
        "evidence": (f"India Code: dc.title=\"{_first(md, 'dc.title')}\" | "
                     f"dc.identifier.act_number=\"{number}\" | "
                     f"dc.date.act_year={_first(md, 'dc.date.act_year')} "
                     f"({item_url})"),
        "assent_date": None,
    }
    enact_date = _first(md, "dc.date.enact_date")
    if enact_date:
        try:
            fields["assent_date"] = datetime.strptime(enact_date.strip(), "%Y-%m-%d")
        except ValueError:
            # Unparseable date stays NULL -- only the exact %Y-%m-%d format counts.
            fields["evidence"] += f" | dc.date.enact_date=\"{enact_date}\" (unparsed)"
    return fields, None


def main() -> int:
    args = parse_args()
    app = create_app()

    with app.app_context():
        query = Act.query
        if args.act_ids:
            ids = [int(x) for x in args.act_ids.split(",") if x.strip()]
            query = query.filter(Act.id.in_(ids))
        elif not args.refresh:
            query = query.filter(Act.act_number.is_(None))
        acts = query.order_by(Act.id).limit(args.limit).all() if args.limit else query.order_by(Act.id).all()
        print(f"acts to process: {len(acts)}")

        stats = {"sourced": 0, "no_exact_match": 0, "unreachable": 0, "skipped": 0}
        session = requests.Session()
        session.headers.update({"User-Agent": UA})
        for idx, act in enumerate(acts, 1):
            try:
                fields, reason = enrich_act(session, act)
                if not fields:
                    unreachable = ("unreachable" in reason or "HTTP 0" in reason
                                   or "HTTP 5" in reason)
                    stats["unreachable" if unreachable else "no_exact_match"] += 1
                    print(f"  [--] {act.id:4d} {act.title[:58]:58s} {reason}")
                else:
                    stats["sourced"] += 1
                    assent = (fields["assent_date"].strftime("%Y-%m-%d")
                              if fields["assent_date"] else "none")
                    print(f"  [ic] {act.id:4d} {act.title[:58]:58s} "
                          f"act_number={fields['act_number']} assent={assent}")
                    if not args.dry_run:
                        act.act_number = fields["act_number"]
                        act.assent_date = fields["assent_date"]
                        act.source = "indiacode"
                        act.source_url = fields["item_url"]
                if not args.dry_run and idx % 25 == 0:
                    db.session.commit()
                    print(f"  ... committed {idx}/{len(acts)}")
            except Exception as exc:
                stats["skipped"] += 1
                print(f"  [!!] act {act.id} failed: {exc}")
            finally:
                time.sleep(args.delay)

        if not args.dry_run:
            db.session.commit()

        print("\nSUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
        rows = db.session.execute(
            db.text("SELECT COALESCE(source,'(null)') s, COUNT(*) n FROM acts GROUP BY s ORDER BY n DESC")
        ).all()
        print("coverage now: " + ", ".join(f"{s}={n}" for s, n in rows))
        total = Act.query.count()
        numbered = db.session.execute(
            db.text("SELECT COUNT(*) FROM acts WHERE act_number IS NOT NULL")
        ).scalar()
        dated = db.session.execute(
            db.text("SELECT COUNT(*) FROM acts WHERE assent_date IS NOT NULL")
        ).scalar()
        print(f"act_number: {numbered}/{total} | assent_date: {dated}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
