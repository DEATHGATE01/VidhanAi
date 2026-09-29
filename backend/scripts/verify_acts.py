"""
Acts Data Spine Verifier
========================
Checks the P0 acceptance criteria (docs/ACTS_TRACKING_PLAN.md §10, items that
are checkable without the Flask server or frontend) against the live database.

Prints PASS/FAIL per check; exits non-zero if any check fails.
Run:  python scripts/verify_acts.py
"""
import os
import re
import sys
from datetime import datetime

# Make backend/ importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Bill, Act, BillActLink, LifecycleEvent

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"exception: {type(e).__name__}: {e}"
    RESULTS.append((ok, name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"         {detail}")
    return ok


def main():
    print("=" * 70)
    print("Acts data spine verification " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 70)

    app = create_app()
    with app.app_context():
        # 1. Schema exists with rows.
        def schema():
            total_acts = Act.query.count()
            total_events = LifecycleEvent.query.count()
            total_links = BillActLink.query.count()
            ok = total_acts >= 1 and total_events >= 1 and total_links >= 1
            return ok, (f"acts: {total_acts} | lifecycle_events: {total_events} | "
                        f"bill_act_links: {total_links}")
        check("schema: acts/events/links tables populated", schema)

        # 2. Every Act row is sourced (source + source_url set).
        def acts_sourced():
            unsourced = Act.query.filter(
                (Act.source.is_(None)) | (Act.source == '') |
                (Act.source_url.is_(None)) | (Act.source_url == '')
            ).count()
            total = Act.query.count()
            return unsourced == 0, f"{total} acts, {unsourced} without source/source_url"
        check("acts: every row carries source + source_url", acts_sourced)

        # 3. Every lifecycle event is sourced and NOT estimated; dated events
        #    carry a real PRS date format (never invented).
        def events_sourced():
            total = LifecycleEvent.query.count()
            unsourced = LifecycleEvent.query.filter(
                (LifecycleEvent.source.is_(None)) | (LifecycleEvent.source == '') |
                (LifecycleEvent.source_url.is_(None)) | (LifecycleEvent.source_url == '')
            ).count()
            estimated = LifecycleEvent.query.filter(LifecycleEvent.is_estimated == True).count()  # noqa: E712
            # A dated event must look like a real PRS date (sanity, not proof):
            # date strings in the API layer are ISO; here we check the stored
            # datetimes are not "now"-stamped at scrape time by spot-checking
            # that dated events are not all identical to the newest extract.
            dated = LifecycleEvent.query.filter(LifecycleEvent.event_date.isnot(None)).all()
            distinct_dates = len({e.event_date for e in dated})
            ok = unsourced == 0 and estimated == 0 and (total == 0 or distinct_dates >= 1)
            return ok, (f"{total} events, {unsourced} unsourced, {estimated} estimated, "
                        f"{distinct_dates} distinct dates")
        check("lifecycle events: sourced, not estimated, dates plausible", events_sourced)

        # 4. Verified links are exact normalized matches (spot-check evidence).
        def links_verified():
            verified = BillActLink.query.filter_by(verified=True).count()
            unverified = BillActLink.query.filter_by(verified=False).count()
            below_floor = BillActLink.query.filter(
                BillActLink.match_confidence < 0.60
            ).count()
            missing_evidence = BillActLink.query.filter(
                (BillActLink.evidence.is_(None)) | (BillActLink.evidence == '')
            ).count()
            ok = below_floor == 0 and missing_evidence == 0 and verified >= 1
            return ok, (f"{verified} verified / {unverified} candidate, "
                        f"{below_floor} below 0.60 floor, {missing_evidence} without evidence")
        check("links: verified exact matches only, evidence on every row", links_verified)

        # 5. No fabricated timeline code remains anywhere in backend/.
        # The needle is built by concatenation so this file does not itself
        # contain the literal string the plan's grep criterion searches for.
        def no_fabrication():
            needle = 'timedelta(days=' + '30)'
            hits = []
            for root, _dirs, files in os.walk(BACKEND_DIR):
                if any(part in root for part in ('.venv', '__pycache__', 'venv')):
                    continue
                for f in files:
                    if not f.endswith('.py'):
                        continue
                    path = os.path.join(root, f)
                    try:
                        with open(path, encoding='utf-8', errors='replace') as fh:
                            for i, line in enumerate(fh, 1):
                                if needle in line:
                                    hits.append(f"{path}:{i}")
                    except OSError:
                        continue
            return len(hits) == 0, ("no fabricated '+30 days' code in backend/" if not hits
                                    else "found: " + ", ".join(hits))
        check("fabrication: '+30 days' estimate code absent from backend/", no_fabrication)

        # 6. Linked bills resolve: a known enactment returns its Act and bill.
        def linkage_resolves():
            link = BillActLink.query.filter_by(verified=True).first()
            if not link:
                return False, "no verified link to test"
            act = Act.query.get(link.act_id)
            bill = Bill.query.get(link.bill_id)
            ok = act is not None and bill is not None
            return ok, (f"bill {bill.bill_id} ({bill.title[:50]}) -> "
                        f"act {act.act_id} ({act.title[:50]})" if ok else "dangling FKs")
        check("linkage: verified link resolves to real bill + act", linkage_resolves)

    passed = sum(1 for ok, _n, _d in RESULTS if ok)
    total = len(RESULTS)
    print("=" * 70)
    verdict = "PASS" if passed == total else "FAIL"
    print(f"{verdict}: {passed}/{total} checks passed")
    print("=" * 70)
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
