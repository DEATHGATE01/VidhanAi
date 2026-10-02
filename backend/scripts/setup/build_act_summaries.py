"""Build the Act dossier for every Act: commencement from its own text, plus a
plain-English summary of the Act.

For each Act: download its official PDF (already linked on the Act page), read the
first pages, extract how it commences, and generate a plain-English summary of the
Act from that same text. Both are stored with provenance (`acts.commencement_note`
/ `acts.commencement_date` and an `act_summaries` row carrying the model version
and the PDF URL).

Usage (from `backend/`):

    python scripts/setup/build_act_summaries.py --dry-run --limit 3
    python scripts/setup/build_act_summaries.py --limit 5          # smoke test
    python scripts/setup/build_act_summaries.py                    # every act
    python scripts/setup/build_act_summaries.py --refresh          # regenerate

Do NOT run two copies at once (they race on the same rows). Summary generation
costs one Groq call per Act and honours 429s; expect a few minutes for 50 Acts.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, ActSummary, db  # noqa: E402
from services.act_dossier import (  # noqa: E402
    USER_AGENT, append_evidence, build_act_summary, extract_commencement, fetch_act_text,
)


def parse_args():
    p = argparse.ArgumentParser(description="Extract Act commencement + build Act summaries.")
    p.add_argument("--act-ids", type=str, default=None, help="comma-separated acts.id values")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--refresh", action="store_true", help="regenerate summaries that exist")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-summary", action="store_true", help="commencement only (no model calls)")
    p.add_argument("--delay", type=float, default=1.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with app.app_context():
        query = Act.query
        if args.act_ids:
            ids = [int(x) for x in args.act_ids.split(",") if x.strip()]
            query = query.filter(Act.id.in_(ids))
        acts = query.order_by(Act.year.desc(), Act.id).all()
        if args.limit:
            acts = acts[: args.limit]
        print(f"acts to process: {len(acts)}")

        stats = {"commencement_date": 0, "commencement_note": 0, "no_commencement": 0,
                 "summarised": 0, "summary_failed": 0, "pdf_failed": 0}

        for idx, act in enumerate(acts, 1):
            existing = ActSummary.query.filter_by(act_id=act.id).first()
            if existing and not args.refresh and not args.no_summary:
                print(f"  [skip ] {act.id:3d} already summarised ({existing.model_version})")
                continue

            text, note = fetch_act_text(act, session)
            if text is None:
                stats["pdf_failed"] += 1
                print(f"  [pdf! ] {act.id:3d} {str(act.title)[:44]:44s} {note}")
                time.sleep(args.delay)
                continue

            when, comm_note, quote = extract_commencement(text)
            if when:
                stats["commencement_date"] += 1
                label = f"date {when.date()}"
            elif comm_note:
                stats["commencement_note"] += 1
                label = comm_note[:52]
            else:
                stats["no_commencement"] += 1
                label = "no commencement provision found in the text"

            produced = model_version = None
            if not args.no_summary:
                produced, model_version = build_act_summary(act, text)
                if produced:
                    stats["summarised"] += 1
                else:
                    stats["summary_failed"] += 1

            print(f"  [{'ok  ' if produced else 'part'}] {act.id:3d} {str(act.title)[:40]:40s} "
                  f"| {label[:50]:50s} | summary={'yes ' + str(model_version) if produced else 'no'}")

            if args.dry_run:
                continue

            if when:
                act.commencement_date = when
            if comm_note:
                act.commencement_note = comm_note
            if quote:
                # Idempotent: overlapping runs must not append the same sentence twice.
                append_evidence(act, f"Commencement from the Act's own text: '{quote}'")

            if produced:
                row = existing or ActSummary(act_id=act.id)
                row.summary = produced
                row.summary_type = "generative"
                row.confidence = 0.8
                row.model_version = model_version
                row.source_url = act.pdf_url
                row.text_chars = len(text)
                row.generated_at = datetime.utcnow()
                db.session.add(row)

            if idx % 5 == 0:
                db.session.commit()
            time.sleep(args.delay)

        if not args.dry_run:
            db.session.commit()

        print("\nSUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
        print("acts with a commencement date:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM acts WHERE commencement_date IS NOT NULL")).scalar(), "/50")
        print("acts with a commencement note:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM acts WHERE commencement_note IS NOT NULL")).scalar(), "/50")
        print("act summary rows:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM act_summaries")).scalar(), "/50")
    return 0


if __name__ == "__main__":
    sys.exit(main())
