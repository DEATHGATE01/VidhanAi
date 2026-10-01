# CTO backlog — self-discovered findings

Owner: CTO-2 (see `docs/CTO_V2.md` §3). One row per finding, **observed not
inferred**, with the exact command or URL that showed it. Add at least three per
pass; never delete a finding — move finished ones to the "Done" table at the
bottom.

Columns: `# | surface | what is wrong (observed) | why it matters | how I saw it | effort | status`

## Open findings

| # | surface | what is wrong (observed) | why it matters | how I saw it | effort | status |
|---|---------|--------------------------|----------------|--------------|--------|--------|
| 1 | Act detail (`/acts/<id>`) | "Act No.", "Assented", "Commenced" render as "Not published by PRS" with no indication that anything was ever looked up. | A reviewer reads this as "the product has no data", not "PRS omits it"; it understates work already done. The DB now stores a per-Act search trail (`acts.lookup_note`, `details_checked_at`) that the page does not show. | Browser on `/acts/digital-personal-data-protection-act-2023` vs `SELECT lookup_note FROM acts` | S | open |
| 2 | Acts data (2026 set) | The 2026 "Act PDFs" on PRS are **Bill texts** with an assent endorsement ("AS PASSED BY BOTH HOUSES", "Bill No. 139-F of 2026"), so no Act number exists in the document; India Code has no 2026 record for them. 13 of 50 acts therefore have an assent date but no number. | An Act with no number on screen looks like a data defect; the reason is real and currently unrecorded per-Act. Also worth checking whether the Gazette (`egazette.gov.in`) publishes the number for these. | `enrich_act_details.py --dry-run --limit 6`; India Code search for the 2026 titles | M | open (partly handled: search trail stored) |
| 3 | Act model / UI | `acts.status` is `unknown` for all 50 acts, and `/acts` still renders a Status column and (conditionally) a status filter for it. India Code exposes `dc.identifier.repealed` (true/false) which maps to Repealed/In force. | A column that is always empty teaches a reviewer to distrust the table. | `/api/acts?per_page=50` → every row `"status": "unknown"` | S | open |
| 4 | Bill pages | Ministry is shown as plain text everywhere; when a value is inferred (`ministry_inferred: true`) nothing on screen distinguishes it from a scraped one, although the summary header does label it. | The project's entire claim is "you can tell sourced from inferred". | `SELECT ministry_source FROM bills` (140 prs / 0 inferred) vs bill card DOM | S | open |
| 5 | Cross-source verification | India Code carries `dc.identifier.ministry_name` + `department_name` per Act (e.g. NRF Act 2023 → "Ministry of Science and Technology") and the Act PDFs carry a "MINISTRY OF ..." line in the Gazette header. Neither is compared against the PRS-derived `bills.ministry`. | A second independent ministry signal is the cheapest possible integrity check on the values the summary prints. | India Code API probe; `pdftotext` of an Act PDF | M | open (tracked as TASKS A7) |
| 6 | `/explore` | 98 of 140 bills have no cached summary and generate one live on first open (3–10 s, or an extractive fallback if Groq rate-limits). Nothing tells the user a summary is being generated vs. unavailable. | A reviewer clicking an uncached bill sees a long pause with no explanation; a 429 makes it degrade silently to the extractive stub. | `regenerate_summaries.py --list`; Groq 429s observed 2026-09-30 07:2x | M | open |
| 7 | Analytics | `/api/analytics/lifecycle-stats` exists but is not surfaced anywhere in the UI. | Work already done, invisible to the reviewer. | `curl /api/analytics/lifecycle-stats` returns data; no page consumes it (`grep -r lifecycle-stats frontend_new/`) | S | open |

## Done (this file's history)

| # | surface | what was wrong | fixed in | verified by |
|---|---------|----------------|----------|-------------|
| I1 | Act detail | A 60% *candidate* link was listed under "Bills This Came From" beside the verified one, distinguished only by a bare "60%". | `b315dcc` | Parent browser check: row now reads "Candidate 60% — not confirmed" + legend |
| I2 | Act detail / `/acts` | Empty fields rendered `—`, Status rendered `unknown`, and a one-value status filter was offered. | `b315dcc` | Parent browser check: "Not published by PRS", no status filter |
| I3 | `/explore` | Page 1 held only unenacted newest bills, so the "Enacted as" chip was invisible without searching. | `695e7fc` | Parent browser check: "100 bills · 20 enacted as Acts (verified)", 12 chips on page 1 |
| I4 | Acts data | 33 of 50 Acts had no number or assent date while their official PDFs stated both on page 1. | `3736281`, `08acc90` | 17/50 enriched, two values confirmed against outside sources |
| I5 | Acts data | An Act page said "Not published by PRS" with no evidence anyone had looked. | `enrich_act_details.py` (this pass) | `acts.lookup_note` populated per Act |

> Findings I1–I5 and rows 1–7 above were inherited from the operator (2026-09-30),
> not discovered by a pass: CTO-1 only acted on what it was told, which is why it
> was replaced. CTO-2 must add its own findings here every pass — the operator
> should never have to point at a placeholder again.
