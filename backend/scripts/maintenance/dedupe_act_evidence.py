"""De-duplicate the provenance fragments stored in `acts.evidence`.

Two enrichment runs overlapping on the same Act append the same sentence twice
(the writers were not idempotent), which then renders twice in the "Evidence for
the values above" line on the Act page. The writers now skip an already-present
fragment (`services.act_dossier.append_evidence`); this repairs the rows written
before that guard existed.

Fragments are joined with ' | '. Only EXACT duplicate fragments are dropped, in
place, keeping the first occurrence and the original order — near-duplicates that
differ in wording are preserved, because they may be different sources agreeing
and that is information, not noise.

Run once:  python backend/scripts/maintenance/dedupe_act_evidence.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402


def dedupe(text: str):
    """Return (new_text, removed_count)."""
    if not text:
        return text, 0
    parts = [p.strip() for p in text.split(" | ")]
    seen, kept, removed = set(), [], 0
    for part in parts:
        if not part:
            removed += 1
            continue
        if part in seen:
            removed += 1
            continue
        seen.add(part)
        kept.append(part)
    return " | ".join(kept), removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Drop duplicate evidence fragments.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        changed = removed_total = 0
        worst = []
        for act in Act.query.order_by(Act.id).all():
            new_text, removed = dedupe(act.evidence or "")
            if removed:
                changed += 1
                removed_total += removed
                worst.append((removed, act.id, str(act.title)[:44]))
                if not args.dry_run:
                    act.evidence = new_text
        if not args.dry_run:
            db.session.commit()

        worst.sort(reverse=True)
        print(f"acts with duplicate fragments: {changed}")
        print(f"fragments removed: {removed_total}")
        for removed, act_id, title in worst[:5]:
            print(f"   {removed} duplicate(s) on act {act_id}: {title}")

        # Independent re-read: verify on the committed values, not the objects.
        still = 0
        for act in Act.query.order_by(Act.id).all():
            _t, removed = dedupe(act.evidence or "")
            if removed:
                still += 1
        label = "dry-run (expected)" if args.dry_run else "repair"
        print(f"acts still holding duplicates after {label}: {still}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
