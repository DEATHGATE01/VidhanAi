"""Regenerate cached bill summaries through the real API code path.

Summaries are cached in `bill_summaries` and served from cache forever, so a bill
whose summary was written by the rule-based extractive fallback (before the Groq
backend worked) keeps showing that stub even after the backend is fixed. This
script re-runs `db_service.get_or_generate_bill_summary`, i.e. exactly what
`/api/bills/<id>/summary` does, for the bills you name -- so what you verify here
is what the demo will serve.

Usage (from `backend/`):

    python scripts/maintenance/regenerate_summaries.py --list            # show cached state
    python scripts/maintenance/regenerate_summaries.py --only-stale      # rebuild non-generative ones
    python scripts/maintenance/regenerate_summaries.py --bill-ids 5,10,32
    python scripts/maintenance/regenerate_summaries.py --all --limit 20  # a batch

Nothing is fabricated: if every backend fails, the summary is written (and
reported) as the extractive fallback exactly as the live API would.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app import create_app  # noqa: E402
from db_service import get_or_generate_bill_summary  # noqa: E402
from models import Bill, BillSummary, db  # noqa: E402

GENERATIVE = ("groq_", "local_ollama_", "local_lora_")


def parse_args():
    p = argparse.ArgumentParser(description="Rebuild cached summaries via the live code path.")
    p.add_argument("--bill-ids", type=str, default=None, help="comma-separated Bill.id values")
    p.add_argument("--all", action="store_true", help="every bill that has content")
    p.add_argument("--only-stale", action="store_true", help="only non-generative cached summaries")
    p.add_argument("--list", action="store_true", help="print cached state and exit")
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()

    with app.app_context():
        if args.list:
            rows = BillSummary.query.order_by(BillSummary.bill_id).all()
            print(f"cached summaries: {len(rows)}")
            for s in rows:
                print(f"  bill {s.bill_id:4d} {s.summary_type:10s} {s.model_version:34s} {s.generated_at}")
            missing = (
                Bill.query.outerjoin(BillSummary, Bill.id == BillSummary.bill_id)
                .filter(BillSummary.id.is_(None))
                .count()
            )
            print(f"bills with no cached summary: {missing}")
            return 0

        if args.bill_ids:
            ids = [int(x) for x in args.bill_ids.split(",") if x.strip()]
        elif args.all or args.only_stale:
            query = Bill.query.join(BillSummary, Bill.id == BillSummary.bill_id)
            if args.only_stale:
                query = query.filter(
                    ~BillSummary.model_version.like("groq_%")
                    & ~BillSummary.model_version.like("local_ollama_%")
                    & ~BillSummary.model_version.like("local_lora_%")
                )
            ids = [b.id for b in query.order_by(Bill.id).all()]
        else:
            print("nothing to do: pass --bill-ids, --only-stale, --all, or --list")
            return 1

        if args.limit:
            ids = ids[: args.limit]
        print(f"regenerating {len(ids)} summaries")

        ok = stale = failed = 0
        for i, bid in enumerate(ids, 1):
            # Drop the cached row so get_or_generate actually regenerates it.
            BillSummary.query.filter_by(bill_id=bid).delete()
            db.session.commit()
            try:
                result = get_or_generate_bill_summary(bid, app)
                if "error" in result:
                    failed += 1
                    print(f"  [!!] bill {bid}: {result['error']}")
                else:
                    mv = result.get("model_version", "?")
                    kind = "generative" if mv.startswith(GENERATIVE) else "FALLBACK"
                    if kind == "generative":
                        ok += 1
                    else:
                        stale += 1
                    print(f"  [{kind:10s}] bill {bid:4d} {mv:34s} {result.get('confidence')}")
            except Exception as exc:
                failed += 1
                print(f"  [!!] bill {bid} raised: {exc}")
            if i % 10 == 0:
                db.session.commit()
                print(f"  ... {i}/{len(ids)}")
            # Space the calls out: the Groq free tier rate-limits bursts, and a
            # 429 mid-batch is what turns a demo summary into an extractive stub.
            time.sleep(3.0)

        db.session.commit()
        print(f"\nDONE generative={ok} fallback={stale} failed={failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
