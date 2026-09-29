# CTO Report — Acts Tracking & Bill → Act Lifecycle

Running log of the overnight CTO passes implementing `docs/ACTS_TRACKING_PLAN.md`
(charter: `docs/CTO_ACTS.md`). Newest pass at the bottom. One section per pass:
what changed, the evidence (real command output produced by the pass lead, not
child self-reports), the children spawned, what is next, what is blocked, and
what the next pass must not redo.

---

## Pass 1 — 2026-09-29 — P0 data spine: recovered, reviewed, verified, committed

**Situation at start.** A previous overnight pass (pre-orchestration prompt, solo)
died mid-P0 without committing, without writing this report, and without pasting
verification evidence. Its working copy was intact on `feature/acts-tracking`:
`backend/models.py` (+143 lines: Act / BillActLink / LifecycleEvent per plan §3),
`backend/routes.py` (+373/−64: fabrication deleted, new acts routes), and five new
untracked files (scraper, linker, sync, migrate, verify). The DB already carried a
real sync result: acts=50, bill_act_links=57, lifecycle_events=406. This pass's
step was therefore **"complete and prove P0, then commit it"** — not re-implement it.

**What changed (this pass).**
- Created `backend/.venv` (uv, Python 3.12) with the minimal P0 dependency set
  (Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-CORS, beautifulsoup4 4.12.2,
  requests 2.31.0, SQLAlchemy ≥2.0.23, Werkzeug, python-dotenv, lxml). The system
  python 3.12.10 has no pip module and the repo's requirements.txt pulls heavy ML
  deps (chromadb, sentence-transformers) P0 does not need. No change to
  `backend/requirements.txt` (charter: none needed for P0).
- Fixed the one actionable review finding (own fix): `Act.short_title` (plan §3)
  was never populated — all 50 rows were NULL. `sync_acts.py` now computes it via
  the linker's `normalize()` (canonical normalizer, single source of truth) from
  the scraped title only, sets it on both insert and update paths, and the update
  path also refreshes `source_url` when PRS changes it. Backfilled: 50/50 acts now
  carry `short_title`.
- Killed a stale server (PID 15988, `C:\Python313\python.exe app.py`, started
  04:58 — before this pass) that was squatting on :5000 and serving 500s for
  `/api/bills/<id>`; it was running old code on the wrong interpreter. See
  "Diagnosis" below.
- No new dates, Act numbers, or metrics invented anywhere; `assent_date`,
  `commencement_date`, `act_number` remain NULL (not on PRS; India Code
  unreachable — P2 enrichment only).

**Orchestration.** One delegation batch, 3 read-only children (≤4, disjoint by
concern, no writers → no clobber risk; `routes.py` owned by the pass lead alone;
all children told: no git commands, no repo writes, honesty rule verbatim):
- `prs-cross-check` — re-fetched the 6 PRS bill pages whose stored timelines
  back the verified links (DB ids 10, 11, 20, 21, 22, 26), compared PRS event
  dates to `lifecycle_events` rows, re-verified the acts listing.
- `code-reviewer` — cold review of the whole uncommitted P0 diff for honesty
  violations, plan conformance (§3/§4/§5/§7), correctness.
- `api-verifier` — curl of the new endpoints on :5000 (health, /api/acts,
  filters, /api/acts/<act_id>, 6× /api/bills/<id>/lifecycle, /api/bills/10).

**Diagnosis: the /api/bills/<id> 500 was the stale server, not the new code.**
The api-verifier reported `GET /api/bills/10 → 500 "[Errno 22] Invalid argument"`.
Re-verified myself:
- My server's log (`process_manage log`, proc_227756b34519) showed a clean startup
  and no traceback — the failing requests never reached it.
- `netstat -ano | grep ":5000" | grep LISTEN` → two listeners: PID 15988
  (`C:\Python313\python.exe app.py`, created 29-09-2026 04:58:23) and PID 19112
  (this pass's venv server, created 05:52:24). On Windows the first binder
  receives connections.
- `powershell Get-CimInstance Win32_Process` identified both PIDs' command lines.
- After `Stop-Process -Id 15988 -Force`: `/api/bills/10` → 200 with the full bill
  payload. The blocker was environmental (stale process from the previous pass),
  not a code defect.

**Evidence — real command output produced by this pass lead (my terminal, not
child self-reports):**

1. `python -m py_compile` on all 7 changed `.py` files:
```
py_compile OK: all 7 changed files
```
(models.py, routes.py, prs_acts_scraper.py, act_linker.py, sync_acts.py,
migrate_acts_tables.py, verify_acts.py)

2. `python backend/scripts/setup/sync_acts.py --limit 50 --delay 0.5` against the
   live DB (after the short_title fix) — idempotent re-run:
```
Fetching acts page 0: https://prsindia.org/acts/parliament
Reached max_items=50; stopping pager walk.
Successfully fetched 50 acts across 1 page(s)

[acts] 0 new / 50 total
[timeline] bills: 140 with url | fetched: 137 | events: 0 (0 dated / 0 undated)
[links] verified: 32 | candidate: 0 | pairs skipped (<0.60): 2214 | bills considered: 110 | acts considered: 50
SUMMARY: acts: 0 new / 50 total | timeline events: 0 new / 406 total | links: 32 verified / 0 candidate
```
(0 new rows on a re-run = idempotent upsert working; the original 50/406/57 were
written by the previous pass's run of the same script.)

3. `python backend/scripts/verify_acts.py`:
```
  [PASS] schema: acts/events/links tables populated
         acts: 50 | lifecycle_events: 406 | bill_act_links: 57
  [PASS] acts: every row carries source + source_url
         50 acts, 0 without source/source_url
  [PASS] lifecycle events: sourced, not estimated, dates plausible
         406 events, 0 unsourced, 0 estimated, 152 distinct dates
  [PASS] links: verified exact matches only, evidence on every row
         32 verified / 25 candidate, 0 below 0.60 floor, 0 without evidence
  [PASS] fabrication: '+30 days' estimate code absent from backend/
         no fabricated '+30 days' code in backend/
  [PASS] linkage: verified link resolves to real bill + act
         bill the-public-examinations-prevention-of-unfair-means-amendment-bill-2026
         -> act public-examinations-prevention-of-unfair-means-act-2026
PASS: 6/6 checks passed
```

4. `grep -rn "timedelta(days=30)" backend/ --include="*.py"` → exit code 1
   (no matches). The raw grep's only hit was a `__pycache__` .pyc (verify_acts's
   own compiled check pattern), not source. The remaining `timedelta` in
   routes.py:1359 is `timedelta(hours=lookback_hours)` — the pre-existing alerts
   lookback, unrelated to the timeline fabrication.

5. Live API (Flask on :5000, this pass's venv server; my python + requests):
```
PASS | health | 200
PASS | GET /api/acts | count=20 total=50
PASS | GET /api/acts?year=2026 | count=5 total=6 years={2026}
PASS | GET /api/acts/<act_id> | linked_bills=2 verified=1 ev_len=0
PASS | lifecycle bill 10 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | lifecycle bill 11 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | lifecycle bill 20 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | lifecycle bill 21 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | lifecycle bill 22 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | lifecycle bill 26 | events=4 types=['enacted_as','introduced','passed_lok_sabha','passed_rajya_sabha'] all_sourced=True
PASS | GET /api/bills/10 timeline sourced-only | timeline_events=3
OVERALL: PASS
```
Every lifecycle event carries `is_estimated=false`, a non-empty `source`
(`prs_billtrack`), and a non-empty `source_url` (the bill's PRS page). The
`enacted_as` event is the Act chain step from the verified link (plan §7).

6. PRS drift spot-check by the pass lead (bill 26, browser User-Agent):
```
HTTP 200
blocks: 3
  Introduced | Lok Sabha | Feb 11, 2026
  Passed | Lok Sabha | Feb 12, 2026
  Passed | Rajya Sabha | Feb 12, 2026
DB rows for bill 26:
  introduced | 2026-02-11 | Lok Sabha
  passed_lok_sabha | 2026-02-12 | Lok Sabha
  passed_rajya_sabha | 2026-02-12 | Rajya Sabha
```
Exact match.

7. `short_title` backfill:
```
acts with short_title: 50/50
  The Industrial Relations Code (Amendment) Act, 2026 -> industrial relations code amendment act | 2026 | prs_acts
```

**Child claims re-checked, kept vs discarded:**
- prs-cross-check's "no drift" verdict: kept — corroborated by my own bill-26
  fetch (§6 above) matching the DB, and by verify_acts's 0 estimated / 0
  unsourced counts. Its per-bill comparison was consistent across all 6 bills
  (18/18 events matched per its report; I independently re-proved one bill and
  the aggregate integrity checks).
- code-reviewer's verdict "ship it" with 9 findings: kept the actionable ones
  (short_title never populated → fixed this pass; source_url not refreshed on
  change → fixed in the same edit). Discarded as wrong: (a) "get_bill_lifecycle
  should filter to verified links" — it already only emits Act-chain events for
  verified links (routes.py: the `if link.verified:` gate), the reviewer
  misread; (b) "ministry bonus is dead code, Act has no ministry column" — true
  but harmless and plan-conformant: the plan's §5.3 bonus applies only when both
  sides have a ministry string, which is exactly what the code does; (c) minor
  style nits (connection hygiene, evidence wording) — noted, not blocking.
- api-verifier's blocker (`/api/bills/10` → 500): kept the signal, discarded the
  attribution — the 500 came from a stale server squatting on the port, not from
  the new code (diagnosis above; my post-kill run returned 200).

**Frontend gate (criterion 6): NOT RUN this pass** — no frontend work has started
(P1 is the next phase). `cd frontend_new && npm run build` is the first gate of
pass 2. No `.cto-stop` was created: criteria 1–5 and 7 are green with evidence,
criterion 6 is pending P1.

**What is next (pass 2+):** P1 — frontend UI: `pages/ActsPage.jsx`,
`pages/ActDetailPage.jsx`, `components/LifecycleTimeline.jsx`, BillCard
"Enacted as" chip, `/acts` route + sidebar entry, `services/api.js`
(`getActs`, `getActById`, `getBillLifecycle`, `syncActs`), then
`npm run build` and a browser pass over `/acts`. P2 (optional): India Code
prober (record the blocker if unreachable — it timed out from this machine on
2026-09-29), state-legislature Acts, lifecycle-stats analytics.

**What is blocked:** nothing blocking P0/P1. India Code (`indiacode.nic.in`)
remains unreachable from this machine (plan §2) — `act_number`/`assent_date` stay
NULL by design until a browser fallback works (P2).

**Next pass must NOT redo:**
- Do not re-implement the P0 files — they are committed as of this pass; work
  from them.
- Do not re-run `sync_acts.py` expecting new rows — it is idempotent and
  up-to-date (50 acts / 406 events / 57 links); only `--bills-only` timelines or
  a P2 enrichment change anything.
- Do not re-verify the fabrication removal — `grep -rn "timedelta(days=30)"
  backend/ --include="*.py"` → empty, confirmed twice.
- Do not re-check the 6 verified links' dates against PRS — done this pass
  (no drift, bill-26 spot-check by the pass lead).
- Do not kill the Flask server started by this pass without checking whether it
  is the only listener on :5000 — the previous pass's stale server (wrong
  interpreter) was the actual cause of the 500s diagnosed above.
- D3 (groq/compound repoint), T2 (frontend security review), T3 (n8n Gmail
  OAuth), T4 (ChromaDB vectorize), T5 (dead-artifact cleanup) remain untouched —
  not this loop's tasks.

**Commits (this pass, on `feature/acts-tracking`):**
- `feat(acts): track Acts as first-class objects and link them to Bills (P0 data spine)`
  — models (Act/BillActLink/LifecycleEvent), PRSActsScraper, act_linker,
  sync_acts.py, migrate_acts_tables.py, verify_acts.py, routes.py (new
  /api/acts* + /api/bills/<id>/lifecycle + /api/admin/sync-acts; fabricated
  timeline deleted).
- `docs(acts): add plan, charter, pass prompt, and pass-1 CTO report`
  — ACTS_TRACKING_PLAN.md, CTO_ACTS.md, CTO_ACTS_PROMPT.md, cto-report-acts.md,
  TASKS.md, SESSION_LOG.md.

Left untracked on purpose: `review_report.json` (scratch artifact the
code-reviewer child wrote to the repo root this pass — not part of the
deliverable; delete or keep at the user's discretion).
