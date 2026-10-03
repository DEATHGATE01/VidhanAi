"""Populate acts.amends / acts.amends_note from each Act's own stored text.

Reads full_text (see backfill_act_full_text.py — this script never hits the network),
extracts the parent statute(s) the Act declares it amends, and stores them.

Honesty rules, matching the rest of the Act pipeline:
  * The evidence string records the Act's own wording, so the UI can show where the
    claim comes from instead of asserting it.
  * A name the PDF's two-column text layer spliced is either reassembled from a
    cleaner occurrence (confidence 'repaired') or flagged 'damaged'. A damaged name
    is never presented as the statute's name.
  * An Act that names no parent is NOT an error: a principal Act amends nothing.
    amends stays NULL and amends_note says which of the two it is.

Usage:
    python scripts/maintenance/extract_act_amendment_targets.py [--act-ids 4,9] [--dry-run]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from services.act_dossier import extract_amendment_targets  # noqa: E402


def note_for(targets, text_len):
    if not targets:
        if not text_len:
            return ("No text stored for this Act (see backfill_act_full_text.py), so the statutes it "
                    "amends have not been read yet.")
        return ("No parent statute named in the Act's own text as read here. Either this is a principal "
                "Act (a new law amends nothing) or the clause sits outside the pages read; the Act's own "
                "PDF is the source either way.")
    parts = []
    for t in targets:
        piece = f"{t['title']}, {t['year']}"
        if t["sections"]:
            piece += f" (section{'s' if len(t['sections']) > 1 else ''} {', '.join(t['sections'])})"
        if t["cited_act_number"]:
            piece += f" [{t['cited_act_number']}]"
        parts.append(piece)
    note = "Statute lineage read from the Act's own text — amends: " + "; ".join(parts) + "."
    if any(t["confidence"] == "repaired" for t in targets):
        note += " One name was reassembled: the PDF's text layer interleaves its two columns."
    if any(t["confidence"] == "damaged" for t in targets):
        note += " One name is unreadable in the PDF's text layer and is identified by year/number only."
    return note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--act-ids", help="comma-separated act ids (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="print findings, write nothing")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        query = Act.query
        if args.act_ids:
            query = query.filter(Act.id.in_([int(x) for x in args.act_ids.split(",") if x.strip()]))
        acts = query.order_by(Act.id).all()

        conf = Counter()
        with_parent = no_parent = no_text = 0
        for act in acts:
            text = act.full_text or ""
            targets = extract_amendment_targets(text)
            if not text:
                no_text += 1
            elif targets:
                with_parent += 1
            else:
                no_parent += 1
            for t in targets:
                conf[t["confidence"]] += 1
            note = note_for(targets, len(text))
            label = targets[0]["title"][:42] if targets else "—"
            print(f"  act {act.id:2d} {str(act.title)[:36]:36s} | {label:42s} | {len(targets)} parent(s)")
            if not args.dry_run:
                act.amends = json.dumps(targets, ensure_ascii=False) if targets else None
                act.amends_note = note
        if not args.dry_run:
            db.session.commit()

        print(f"\nSUMMARY acts_with_parent={with_parent} principal_or_unread={no_parent} "
              f"no_text={no_text} | entries {dict(conf)}")
        if not args.dry_run:
            stored = Act.query.filter(Act.amends.isnot(None)).count()
            print(f"acts with stored lineage: {stored} / {Act.query.count()}")


if __name__ == "__main__":
    main()
