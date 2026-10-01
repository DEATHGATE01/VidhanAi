"""Repair the machine-generated header of already-cached summaries in place.

WHY
The summary header ("## Title / **Ministry:** / **Status:** / **Introduced:**") is
built by `ai_service._format_header` in Python BEFORE the LLM writes the body, and
it is stored as part of `bill_summaries.summary`. Until 2026-10-01 that function
fell back to `date_scraped`, so all 42 cached summaries stored a header reading
"**Introduced:** August 18, 2026" (the scrape date) whatever the bill's real year.
Fixing the function does not touch text already stored, so those rows keep showing
the wrong date until repaired.

This rebuilds the header with the SAME function (never hand-edited text) using the
bill's now-backfilled `introduction_date`, and splices it back in front of the
untouched LLM body. Only the header is regenerated -- the body is byte-identical,
so `model_version` still describes the text truthfully. Each repaired row is
stamped with `header_repaired_at` so the edit is visible rather than silent.

The alternative -- regenerating all 42 through the LLM -- was rejected: it costs
42 model calls against a rate-limited free tier, can degrade a summary to the
extractive fallback hours before a demo, and would rewrite bodies that are not
wrong. A header the system itself generates is the system's to correct.

Usage (from `backend/`):

    python scripts/maintenance/repair_summary_headers.py --dry-run
    python scripts/maintenance/repair_summary_headers.py
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

DB_PATH = os.path.join(BACKEND_DIR, "instance", "regulation_alert.db")
BODY_MARKER = "\n\n### "


def ensure_column(con: sqlite3.Connection) -> bool:
    existing = {r[1] for r in con.execute("PRAGMA table_info(bill_summaries)")}
    if "header_repaired_at" in existing:
        return False
    con.execute("ALTER TABLE bill_summaries ADD COLUMN header_repaired_at DATETIME")
    con.commit()
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild cached summary headers with the correct introduction date.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from datetime import datetime
    from ai_service import _format_header  # the same function that wrote the header

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    if not args.dry_run:
        if ensure_column(con):
            print("added column: bill_summaries.header_repaired_at")

    rows = con.execute("""
        SELECT s.id AS sid, s.summary, b.id AS bid, b.title, b.ministry, b.status,
               b.ministry_source, b.introduction_date, b.date_scraped
        FROM bill_summaries s JOIN bills b ON b.id = s.bill_id
        WHERE s.summary IS NOT NULL
        ORDER BY b.id
    """).fetchall()
    print(f"cached summaries: {len(rows)}")

    repaired = unchanged = skipped = 0
    for r in rows:
        text = r["summary"]
        if BODY_MARKER in text:
            _old_header, body = text.split(BODY_MARKER, 1)
            body = BODY_MARKER.lstrip("\n") + body
        else:
            skipped += 1
            print(f"  [skip] bill {r['bid']:4d} no '{BODY_MARKER.strip()}' marker — left untouched")
            continue
        new_header = _format_header(r["title"], r["ministry"], r["status"],
                                   r["introduction_date"], r["date_scraped"],
                                   r["ministry_source"])
        new_text = new_header + "\n\n" + body
        if new_text == text:
            unchanged += 1
            continue
        old_line = next((l for l in _old_header.splitlines() if "Introduced:" in l), "(no Introduced line)")
        new_line = next((l for l in new_header.splitlines() if "Introduced:" in l), "(line omitted)")
        print(f"  [fix ] bill {r['bid']:4d}  {old_line.strip() or '(none)'}  ->  {new_line.strip() or '(none)'}")
        if not args.dry_run:
            con.execute("UPDATE bill_summaries SET summary=?, header_repaired_at=? WHERE id=?",
                        (new_text, datetime.utcnow(), r["sid"]))
        repaired += 1

    if not args.dry_run:
        con.commit()

    print(f"\nSUMMARY repaired={repaired} already_correct={unchanged} skipped={skipped}")
    # Meaningful invariant: the stored header must agree with the bill's OWN
    # sourced introduction_date. Counting "2026 dates" would be meaningless --
    # these are 2026 bills, so a correct introduction date is often in 2026.
    mismatch = 0
    for r in con.execute("""
            SELECT s.summary, b.id AS bid, b.introduction_date
            FROM bill_summaries s JOIN bills b ON b.id = s.bill_id
            WHERE s.summary IS NOT NULL"""):
        text = r["summary"]
        want = None
        if r["introduction_date"]:
            try:
                from datetime import datetime as _dt
                want = _dt.fromisoformat(str(r["introduction_date"]).replace("Z", "+00:00")).strftime("%B %d, %Y")
            except Exception:
                want = None
        line = next((l for l in text.splitlines() if "Introduced:" in l), None)
        got = line.split("**Introduced:**", 1)[1].replace("  ", "").strip() if line else None
        if want != got:
            mismatch += 1
            print(f"  MISMATCH bill {r['bid']}: header says {got!r}, "
                  f"bills.introduction_date says {want!r}")
    print(f"cached summaries whose header disagrees with the sourced introduction date: {mismatch}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
