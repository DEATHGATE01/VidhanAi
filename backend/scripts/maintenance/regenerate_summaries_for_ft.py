"""Regenerate bill summaries with the currently-enabled generative backends.

Why this exists: ``get_or_generate_bill_summary`` returns the DB-cached summary
if one exists, so summaries generated earlier by another backend (e.g. Groq on
the public deploy) would mask the locally fine-tuned model. This script deletes
the cached ``BillSummary`` row for the chosen bills and regenerates them under
whatever backends are enabled right now (Ollama fine-tuned model → local LoRA →
Groq), then prints the resulting ``model_version`` so you can SEE which engine
produced the text.

Run from backend/::

    # Fine-tuned model on the demo box (Ollama up, no GROQ_API_KEY needed):
    VIDHANAI_USE_OLLAMA=1 python scripts/maintenance/regenerate_summaries_for_ft.py 12 45 67
    # Or nuke + regenerate every bill that has full text:
    VIDHANAI_USE_OLLAMA=1 python scripts/maintenance/regenerate_summaries_for_ft.py --all

Recommend regenerating only the handful of bills you will demo: each fresh
summary from the 3B model on CPU takes tens of seconds, and the result is then
DB-cached for instant subsequent loads.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Make the backend/ package importable when run from anywhere.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Bill, BillContent, db  # noqa: E402
import db_service  # noqa: E402

# Model_version prefixes that mean "the fine-tuned model produced this".
FINETUNED_PREFIXES = ("local_ollama_", "local_lora_")


def _one_line(text: str, width: int = 140) -> str:
    return " ".join((text or "").split())[:width]


def regenerate_bill(bill: Bill, flask_app) -> dict:
    """Delete any cached summary for ``bill`` and regenerate it.

    Returns a short status dict for reporting.
    """
    # Drop the cached row so get_or_generate actually regenerates.
    if bill.summary is not None:
        db.session.delete(bill.summary)
        db.session.commit()

    t0 = time.time()
    result = db_service.get_or_generate_bill_summary(bill.id, flask_app)
    elapsed = time.time() - t0

    if "error" in result:
        return {"bill": bill, "ok": False, "note": result["error"], "elapsed": elapsed}

    return {
        "bill": bill,
        "ok": True,
        "summary_type": result.get("summary_type"),
        "model_version": result.get("model_version"),
        "elapsed": elapsed,
        "summary": result.get("summary", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bill_specs", nargs="*", help="DB numeric ids or PRS bill_id strings")
    parser.add_argument("--all", action="store_true",
                        help="Regenerate every bill that has full text (can be slow)")
    args = parser.parse_args()

    if not args.bill_specs and not args.all:
        parser.print_help()
        return 2

    app_ = create_app()
    with app_.app_context():
        bills: list[Bill]
        if args.all:
            bills = (
                Bill.query
                .join(BillContent, BillContent.bill_id == Bill.id)
                .filter(BillContent.full_text.isnot(None))
                .all()
            )
            print(f"[ok] --all: {len(bills)} bill(s) with full text")
        else:
            bills = []
            for spec in args.bill_specs:
                bill = None
                try:
                    bill = db.session.get(Bill, int(spec))
                except (ValueError, TypeError):
                    pass
                if bill is None:
                    bill = Bill.query.filter_by(bill_id=str(spec)).first()
                if bill is None:
                    print(f"[warn] no bill matches {spec!r}; skipping")
                    continue
                if bill.content is None or not bill.content.full_text:
                    print(f"[warn] bill {bill.id} has no full text; skipping (id={bill.id})")
                    continue
                bills.append(bill)

        print(f"[info] generating {len(bills)} summary(ies) with current backends...")
        if not bills:
            print("[warn] nothing to regenerate")
            return 0

        ok = 0
        for bill in bills:
            out = regenerate_bill(bill, app_)
            if not out["ok"]:
                print(f"[err ] bill {bill.id} failed: {out['note']}")
                continue
            ok += 1
            mv = out.get("model_version") or "?"
            marker = (
                "FT" if any(str(mv).startswith(p) for p in FINETUNED_PREFIXES)
                else "GROQ" if "groq" in str(mv)
                else "EXTRACTIVE/degraded"
            )
            print(
                f"[{marker:>18}] bill {bill.id} | {mv} | {out.get('summary_type')} "
                f"| {out['elapsed']:.1f}s"
            )
            print(f"      {_one_line(out.get('summary', ''))}")

        print(f"[done] regenerated {ok}/{len(bills)} summary(ies).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
