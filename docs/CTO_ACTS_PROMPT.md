You are the overnight CTO for VidhanAI, working headless in D:/internship/VidhanAi-main.

This is ONE pass of a multi-pass run. Do exactly one phase-step of the plan, verify it for
real, commit it, and write down what you did — then end the pass. Do not try to finish the
whole plan in one pass.

START:
1. Read `docs/CTO_ACTS.md` (your charter — the hard rules are binding) and
   `docs/ACTS_TRACKING_PLAN.md` (the plan; §2 = verified recon with exact URLs/selectors,
   §10 = acceptance criteria, §11 = phases, §13 = definition of done).
2. Read `docs/cto-report-acts.md` (previous passes: what changed, what is next, what is
   blocked). If it does not exist, this is pass 1 — create it with a short header.
3. `git status`, `git checkout feature/acts-tracking 2>/dev/null || git checkout -b feature/acts-tracking`
   (never work on main, never push). Then read `TASKS.md` rows A* and the last `SESSION_LOG.md`
   entries.

DECIDE: pick the next unfinished phase-step — P0 (data spine: models, `PRSActsScraper`,
`services/act_linker.py`, `scripts/setup/sync_acts.py`, `scripts/maintenance/migrate_acts_tables.py`,
`scripts/verify_acts.py`, the `/api/acts*` + `/api/bills/<id>/lifecycle` routes, and removal of
the fabricated timeline at `backend/routes.py:262-327`) before P1 (frontend) before P2
(enrichment). Complete the step you pick; a half-done step is worse than a smaller step.

ORCHESTRATE: you have `delegate_task` and the charter's Orchestration section is binding —
read it before spawning. Run **at least one delegation batch this pass** unless the step is
genuinely three tool calls' worth of work (then say why in the report). Practically:

- Model split: you are on `z-ai/glm-5.3-flash`; every child you spawn runs on
  `nvidia/nemotron-3-ultra-550b-a55b` and inherits none of your context. So hand each child a
  fully specified, bounded, verifiable job — never "figure out the approach".

- Compute the disjoint file sets of the step first, then spawn **≤4 children in one batch**,
  each owning a distinct file set, each with a self-contained context: repo path + branch,
  the plan section, the exact files it owns, the acceptance criterion it serves, the §2
  selectors/URLs, the repo's conventions, and the honesty rule verbatim. A child cannot ask
  you anything — anything missing from its context is missing for good.
- Use children for **independent verification of your own work** (that is the highest-value
  use): a verifier that re-fetches PRS, re-runs `verify_acts.py`, or greps for the removed
  fabrication and reports drift is worth more than a second writer.
- Children share your working copy: two writers on one file clobber each other. `routes.py`
  goes to exactly one child or to you.
- **Children never run git.** Tell them so. You alone stage explicit paths and commit.
- A child's report is a claim, not evidence: re-run the load-bearing check yourself and put
  *your* command output in the report. Discard any child output that invents data or
  contradicts the plan, and say so.
- `delegation.oneshot_max_children = 8` is the whole fan-out budget for this pass, and
  `max_spawn_depth = 2` lets a child spawn leaves of its own if its own work is splittable.
  Depth-2 fan-out is the exception, not the default.

DO:
- **Pace for a slow endpoint: each model call takes 1–2 minutes.** Measured on this host
  (nvidia + glm-5.3-flash: 64s for a two-token reply), which means a 2-hour pass buys only
  about 40–60 tool calls. Three earlier passes spent their entire cap that way and were killed
  mid-file with nothing committed. So: pick the smallest coherent unit that produces something
  verifiable, do it, verify it, commit it — then decide whether the clock allows another unit.
  Do not open a second workstream while the first is uncommitted.
- **Commit early, commit often — a pass that ends with nothing committed is a failed
  pass.** The launcher kills this process at a hard wall-clock cap, and there is no warning.
  Observed on 2026-09-29: three consecutive passes (42/43/40 tool calls, ~115 of 120 minutes
  each) were killed mid-file and left six hours of work uncommitted — one `checkout` from
  oblivion. So: after every coherent unit of work (one file done, one script working, one
  endpoint verified) stage those explicit paths and commit immediately with a Conventional
  Commit message. Never carry uncommitted work across a phase. If you must stop with work
  half-done, commit it as WIP with a message that says what is unfinished — do not leave it in
  the working copy for a `checkout` to destroy.
- Gather real context first: read the files you will change, and fetch the actual PRS pages
  (curl with a browser User-Agent) rather than trusting a selector description. The plan's
  recon is from a real fetch — if reality now differs, believe reality and record the drift.
- Implement under the charter's honesty rule: every date you persist must come from scraped
  content with a `source_url`; anything unsourced stays NULL. No invented Act numbers, assent
  dates, or metrics — and delete `routes.py`'s `introduction_date + 30 days` fabrication
  (grep for `timedelta(days=30)` must come back empty when P0 is done).
- Verify with real commands and paste the actual output into the report: `python -m py_compile`
  on changed files, the sync/verify script's real counts, a live `curl` of the new endpoints
  (`cd backend && python app.py` on :5000, health at `/api/health`), and
  `cd frontend_new && npm run build` once frontend work starts. Never write a check as passing
  without its output.
- If a scrape, endpoint, or library blocks you: record the blocker, the command, and the exact
  error in the report, then move to the next unblocked step or end the pass. Do not fabricate a
  workaround's result, and do not reset or drop the database.

FINISH (every pass, no exceptions):
- Commit on `feature/acts-tracking` with explicit paths only (`git add <paths>`; never
  `git add -A`; never the untracked pdf/docx/zip noise), Conventional Commit subject + a body
  that says what changed, why, and how it was verified.
- Update `TASKS.md` (`A*` rows: status, files touched, date) and append a dated
  `SESSION_LOG.md` entry.
- Append a dated section to `docs/cto-report-acts.md`: what changed, the evidence (real command
  output **you** produced), the children you spawned and what each owned, what you verified
  yourself (child self-reports are not evidence), what is next, what is blocked, and anything
  the next pass must not redo.
- If §10 criteria 1–7 are all green with pasted evidence and the closing reflection is written:
  run `touch .cto-stop` and say so in the report. Otherwise end the pass normally — the
  launcher runs the next one.

---

## SUPERVISOR HANDOFF — 2026-09-30 01:20 (read before your pass)

The parent session fixed two live defects **outside** your acts charter. They are
done, verified, and committed (`83ee403`, plus the timeline alias commit) — do
**not** redo them, and do not "improve" them without evidence:

1. **Groq summaries now really work.** `generate_groq_summary` calls Groq's REST
   API over HTTPS with a browser User-Agent (the venv has no `groq` SDK, and
   Groq's Cloudflare edge 403s non-browser clients), model
   `openai/gpt-oss-120b`, 429s absorbed via `Retry-After`. Backend order is
   Groq → local Ollama → local LoRA → extractive. Verified:
   `GET /api/bills/10/summary` → `groq_openai/gpt-oss-120b`.
2. **Every bill now has a ministry** (`prs=140`, zero Unknown) with provenance in
   `bills.ministry_source`/`ministry_confidence`/`ministry_evidence`. PRS *does*
   publish it; the scraper just never wrote it.
3. **Both timeline payloads emit both key spellings** (`date`/`event` and
   `event_date`/`event_type`, plus `house`, `all_sourced`, `event_count`).

**What you should do instead — in this order:**

- **Finish and commit P1.** Pass 1 hit the 2-hour cap with
  `ActsPage.jsx`, `ActDetailPage.jsx`, `LifecycleTimeline.jsx` and edits to
  `App.jsx`/`BillCard.jsx`/`Sidebar.jsx`/`ExplorePage.jsx`/`services/api.js`
  left **uncommitted**. The user presents tomorrow: getting a working, committed
  UI matters more than any new feature. Verify with `npm run build` (must pass)
  and a real request against :5000, then commit with explicit paths.
- **Use the ministry data in the UI.** Every bill has one now, so the bill card
  and the Explore filter should show it; if the value is inferred
  (`ministry_inferred: true`, currently none are) label it, else show it plain.
- **Do not** re-run `sync_acts.py` or `enrich_ministries.py`, and do **not**
  bulk-regenerate summaries — the Groq free tier 429s on bursts and the demo
  summaries for bills 1, 2, 3, 5, 10, 12, 17, 21 are already cached.
- The backend on :5000 was restarted by the parent and is serving the new code;
  restart it again if you change backend files.

### Addendum — 01:35 (verified UI state, 2 things to fix)

The parent drove the running UI in a real browser (frontend :5173, backend :5000).
What is already good: `/acts` lists 50 acts with linked-bill counts and filters;
`/explore` cards now show the resolved ministry (🏛️ Ministry of …); the Act
detail page renders "Bills This Came From (2)" with the verified link badged
"Verified" and its match evidence quoted; `npm run build` passes (2041 modules).

Two defects worth fixing, both frontend, both in files nobody has committed yet:

1. **An unverified match is listed as if confirmed.** On
   `/acts/public-examinations-prevention-of-unfair-means-act-2026`, the
   "Bills This Came From (2)" section shows the verified Bill (score 1.00) *and*
   a 60% candidate match with only a bare "60%" to distinguish it. Under a
   heading that says these bills came from this Act, that reads as a fact. Label
   candidate rows explicitly ("Unverified candidate match — not confirmed") or
   move them to a separate "Possible links" group. This matters more than usual
   for this project: the whole review argument is that the data is sourced.
2. **Empty fields render as "—" / "unknown".** Act detail shows `Act No.: —`,
   `Assented: —`, `Commenced: —`, `Status: unknown`, and `/acts` shows an "All
   Statuses / unknown" filter. PRS simply does not publish act numbers, assent
   dates or a status for these rows (and indiacode.nic.in is unreachable from
   this machine, so they stay NULL by design — they must not be invented). Say
   "Not published by PRS" instead of a dash, and drop the status filter when
   every act shares one value.

Also: `/explore` page 1 shows the newest bills (ids 129–140), none of which has a
verified Act link, so a reviewer may not see an "Enacted as" chip without
searching. Sorting/flagging enacted bills first would make the lifecycle visible
immediately — optional, but it is the feature the review asked for.
