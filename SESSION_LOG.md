# SESSION_LOG.md — Session Diary

Chronological diary of what happened each session. See `CLAUDE.md` §5.2:
append at session start (what you intend to work on) and at session end
(what you did, what changed, what's unresolved, what the next session
should know). Prose, not just task status.

Newest entries at the TOP, oldest at the bottom.

---

## 2026-09-29 — Session: overnight CTO pass 1 (acts loop) — P0 data spine completed, verified, committed

**Intended:** One pass of the multi-pass overnight CTO run for Acts tracking
(docs/CTO_ACTS.md charter): pick the next unfinished phase-step, verify it for
real, commit it, write the trail, end the pass.

**What happened:**
- Found pass 1 of this loop (pre-orchestration prompt, solo) dead mid-P0 without
  committing or reporting: working copy intact on feature/acts-tracking
  (models.py +143: Act/BillActLink/LifecycleEvent; routes.py +373/−64:
  fabrication deleted + new acts routes; 5 new backend files), DB already synced
  (acts 50 / bill_act_links 57 / lifecycle_events 406). Step became "complete
  and prove P0, then commit".
- Created backend/.venv (uv, py3.12) with the minimal P0 deps (system python has
  no pip; requirements.txt pulls heavy ML deps P0 does not need).
- Ran one delegation batch of 3 read-only verifiers (≤4 per charter; no writers,
  no git for children): PRS cross-check of the 6 verified-link bill timelines,
  cold code review of the P0 diff, live-API curl of the new endpoints.
- Diagnosis (own verification): the api-verifier's /api/bills/10 → 500
  "[Errno 22]" came from a STALE server left by the earlier pass — PID 15988,
  C:\Python313\python.exe app.py, started 04:58, first binder on :5000, running
  old code on the wrong interpreter. Killed it; /api/bills/10 → 200 on this
  pass's venv server. The 500 was environmental, not the new code.
- Applied the one actionable review finding: Act.short_title was never populated
  (50/50 NULL) — sync_acts.py now computes it via act_linker.normalize() from
  the scraped title, sets it on insert+update, refreshes source_url on change.
  Backfilled 50/50.
- Verified (own output in docs/cto-report-acts.md): py_compile clean on 7 files;
  sync re-run idempotent (0 new rows); verify_acts.py PASS 6/6; live API —
  /api/acts, ?year=2026 filter, /api/acts/<act_id> with verified link, 6×
  /api/bills/<id>/lifecycle every event sourced+unestimated, /api/bills/10
  timeline sourced-only — OVERALL PASS; grep timedelta(days=30) backend/*.py
  → empty; own PRS spot-check (bill 26) matches DB exactly.
- Committed on feature/acts-tracking (explicit paths, 2 commits: feat P0 spine,
  docs plan/charter/report/trail). Never pushed.

**Unresolved / next session should know:**
- Criterion 6 (npm run build + /acts page) is pending — P1 frontend is the next
  pass; no .cto-stop this pass.
- India Code unreachable from this machine — act_number/assent_date stay NULL
  (P2 optional enrichment).
- Deferred review nits (non-blocking): evidence-string wording in act_linker,
  connection hygiene in migrate_acts_tables, /api/admin/sync-acts commits
  per-item instead of batching (canonical path is sync_acts.py).
- The Flask server started this pass (venv, PID 19112) may still be running on
  :5000 — check who listens before starting another (stale-server incident
  above).
- Full details and evidence: docs/cto-report-acts.md, pass 1 section.

---

## 2026-09-29 — Session: Acts tracking (review feedback) — plan + overnight CTO handoff

**Intended:** A reviewer asked why the project tracks Bills but not Acts — "the Bill is
not the law, the Act is" — and asked for Acts to be tracked and linked to Bills so the
lifecycle is visible. Plan that work properly and hand it to the overnight CTO loop.

**What happened:**
- Confirmed the gap is real and worse than "missing": there is no Act entity anywhere in
  `backend/models.py`, and the bill timeline at `backend/routes.py:262-327` **invents** its
  dates — "passed" is `introduction_date + 30 days`, withdrawn/lapsed events are stamped
  `datetime.utcnow()`. The reviewer's complaint is precisely that the product asserts a
  lifecycle it does not track.
- Re-verified the PRS India data we would rely on, by real HTTP fetch (not from memory):
  `https://prsindia.org/acts/parliament` → 200 with 549 Act PDF rows
  (`div.views-row` → `div.views-field-title-field a[title]`, PDF under
  `/files/bills_acts/acts_parliament/<year>/`); the working bills list is
  `https://prsindia.org/billtrack/category/billtrack` (975 rows; **`/billtrack/parliament` is a
  404**); each bill detail page carries a real status timeline in
  `div.field-collection-item-field-own-status-details` (`field-own-status` state,
  `-own-status-title` house, `-own-status-date .date-display-single` date). PRS publishes **no
  bill→act link**, so the relationship has to be derived by title normalization + status — which
  is why the plan stores match confidence/evidence and only marks a link `verified` on an exact
  match. `indiacode.nic.in` timed out from this machine (curl HTTP 000) — Act number and assent
  date are therefore explicitly optional enrichment that stays NULL if unsourceable.
- Wrote `docs/ACTS_TRACKING_PLAN.md`: schema (`acts`, `bill_act_links`, `lifecycle_events`),
  `PRSActsScraper`, deterministic `act_linker.py`, `sync_acts.py`, API surface
  (`/api/acts`, `/api/acts/<id>`, `/api/bills/<id>/lifecycle`, `/api/admin/sync-acts`), frontend
  (`ActsPage`, `ActDetailPage`, `LifecycleTimeline`, BillCard "Enacted as" chip), migration,
  P0/P1/P2 phasing, 7 acceptance criteria, and the honest limits.
- Wrote the charter `docs/CTO_ACTS.md` (hard rules: never fabricate a date/Act number, never
  commit to `main` or push, explicit-path staging only, don't touch D3/T2–T5) and the per-pass
  prompt `docs/CTO_ACTS_PROMPT.md`, then launched the overnight loop
  (`~/AppData/Local/hermes/scripts/cto-overnight-acts.sh`, 5 passes, 10 min apart, 2 h cap per
  pass) which works on branch `feature/acts-tracking` and stops itself via `.cto-stop`.

- Enabled real orchestration for the loop: the installed build caps a finite one-shot pass at
  `delegation.oneshot_max_children` (default **2**) with `max_spawn_depth` 1 (no
  sub-subagents) — i.e. the CTO could barely fan out. Set `oneshot_max_children=8` and
  `max_spawn_depth=2` via `hermes config set` (never hand-edited), leaving
  `max_concurrent_children=10`. Added an Orchestration section to `docs/CTO_ACTS.md` (one
  writer per file, only the CTO touches git, child reports are claims not evidence, steer
  children with `action="steer"` rather than re-spawning, ≤4 per batch, context written in full
  because children can't ask questions) and an ORCHESTRATE step to the pass prompt requiring
  ≥1 delegation batch per pass.
- Pass 1 was already running on the pre-orchestration prompt when the config landed (config is
  read at process start), so it works solo; passes 2–5 fan out. Verified live: pass 1 is
  mid-P0, analysing real PRS data ("acts total on page0: 550 | 2026 acts: 6, strong bills: 110")
  and prototyping the title-normalisation linker offline before writing files.

- Model split per the user: the CTO pass runs **`z-ai/glm-5.3-flash`** (now pinned in the
  launcher with `-m`/`--provider nvidia`, so the loop no longer follows the interactive default
  model), and every subagent runs **`nvidia/nemotron-3-ultra-550b-a55b`** via
  `delegation.model` + `delegation.provider=nvidia`. Both ids verified to exist on the nvidia
  endpoint (`/v1/models`: `z-ai/glm-5.3-flash`, `nvidia/nemotron-3-ultra-550b-a55b`). Routing
  proven end-to-end with a real child spawn: child session `20260929_045106_d43af0` ran on
  nemotron-3-ultra (1 API call, 16,415 in / 56 out tokens) — a bare child costs ~16k input
  tokens before it does any work, which is why the charter forbids delegating trivia.

- Pass 1 of the first launch ran on the pre-orchestration prompt, and before it was stopped it had
  already written the P0 files (04:26–04:54): `backend/src/scraping/prs_acts_scraper.py`,
  `backend/services/act_linker.py`, `backend/scripts/setup/sync_acts.py`,
  `backend/scripts/verify_acts.py`, `backend/scripts/maintenance/migrate_acts_tables.py`, plus
  `backend/models.py` (+143: `Act`, `BillActLink`, `LifecycleEvent`) and `backend/routes.py`
  (+373/−64: `/api/acts`, `/api/acts/<act_id>`, `/api/bills/<bill_id>/lifecycle`, and the fabricated
  `introduction_date + 30 days` timeline deleted — `grep -rn "timedelta(days=30)" backend/` now only
  matches stale `.pyc` files). All of it compiles under `python -m py_compile`.
- The loop was then stopped and relaunched **on purpose**: (a) editing a running bash script is
  unsafe (bash re-reads by byte offset, so inserted lines can corrupt the loop), and (b) the first
  pass was on the pre-orchestration prompt with the old delegation caps. The cost was only the
  uncommitted commit + `docs/cto-report-acts.md`; the code stayed on disk and the new pass reads it as
  its starting state instead of redoing it.

**Unresolved / next session should know:**
- The loop writes to `docs/cto-report-acts.md` (new file) — read it first to see how far it got.
- Nothing is pushed; review `feature/acts-tracking` and open a PR when satisfied. The plan's §10
  criteria are the merge gate, and criterion 5 is `grep -rn "timedelta(days=30)" backend/` → empty.
- Untracked repo noise (Course handout PDF, `*.docx`, `results.zip`, `UI_TEST_REPORT.md`,
  `vid-mascot-preview.html`, `synopsis_spec.json`) is deliberately left uncommitted; the loop is
  told to stage explicit paths only.
- Acts beyond Parliament (`/acts/states`) and India Code enrichment are P2, not required.

---

## 2026-09-21 — Session: synopsis rebuild after 5/10 Phase-1 feedback

**Intended:** Professor trashed the simple synopsis ("there is nothing in this
synopsis", 5/10) and gave feedback to research: agent entropy, summarization
evaluation, proper approach, architecture, summarization verification, and
better prompting strategy (fine-tuning vs prompting). User added
`Course_Handout__Agentic AI (4).pdf` (CSE3101, Dr. Soharab Hossain Shaikh,
BMU). Plan: spawn 4 parallel research agents for verified citations, then
rebuild the synopsis with real technical depth that answers each feedback
point, aligned to the handout's Phase-1 rubric (C2 objectives/outcomes,
C3 methodology/charter, C4 feasibility + timeline, C5 individual/team matrix).
Note from handout: roles must ROTATE across phases; public GitHub repo
mandatory; Phase-2 (30%) is progress-vs-plan + working prototype.

**What happened:**
- Diagnosed the 5/10: `VidhanAI_Synopsis_Report_v2.docx` describes the app but states no
  hypotheses, metrics, experiments or citations, and covers none of the handout's
  "Critical Play Areas" (LLM by trainable params + entropy, architecture, protocol,
  per-agent latency/accuracy via LLM-as-judge, >= 40 traced runs).
- Ran 4 parallel research passes (entropy/uncertainty, summarization evaluation +
  verification, prompting vs fine-tuning, architecture/protocols/observability) and one
  read-only code audit. First attempt failed: the environment's default subagent model
  (`deepseek/deepseek-v4-flash-0731`) returned 404; relaunched with `model: sonnet`.
- Re-checked the four numbers most likely to be quoted against primary pages (Magesh
  17-33%, Farquhar SE AUROC 0.790 vs 0.691 with 10 generations, MiniCheck "400x lower
  cost", Groq deprecation). All matched.
- Wrote `docs/RESEARCH_BRIEF.md` (evidence base, design proposals, honest gap table,
  viva questions, unverified list), `docs/synopsis/build_synopsis_v3.py` and generated
  `VidhanAI_Synopsis_Report_v3.docx` (2 pages: Section 1 abstract/methodology, Section 2
  plan + rotating responsibility matrix). Checked by exporting to PDF through Word.
- Section 3 (individual understanding) was deliberately NOT written: the handout grades
  it by viva and treats AI-generated work as an academic-integrity matter, so the brief
  gives per-role prompts (section 9) for each member to answer in their own words.

**Findings the next session must know (audit, 2026-09-21):**
- `groq/compound` was SHUT DOWN by Groq on 2026-09-21 (no replacement listed). The LLM
  agent and Groq fallback now error. Logged as TASKS D3 (not fixed; out of scope here).
- Only one real LLM agent exists; the other "agents" are plain functions. ChromaDB has 0
  embeddings. Fact-check is regex-only and is skipped when retrieval is empty. 0 runs are
  persisted. Existing eval is n=5, CIs overlap, reference = teacher LLM output, scored
  bills now sit in `train.jsonl`.
- `docs/IEEE_Report.md` contradicts the code and `generate_extra_charts.py` plots
  hard-coded numbers: do not cite either as evidence.
- Everything in the synopsis about entropy, ablation, verification and architecture is a
  PLAN with targets, not a result. Do not turn targets into reported numbers.

**Follow-up (same day):** professor also asked for a literature review stating whether
this work was done before, plus flowcharts. Ran a dedicated gap-analysis pass (~55 queries),
re-fetched 6 key abstracts (LLaMandement, HASSUM, Kulkarni, L-MARS, NyayaAI, FENICE).
It CORRECTED an earlier overstatement: amendment summarization is not unexplored
(LLaMandement summarizes French amendments); what is not found is version-to-version bill
summaries with verification. HASSUM (semantic entropy in a hierarchical MAS) is a close
neighbour, so the synopsis says "combination in a new domain", never "first". Added
synopsis section 1.2 (lit review table + "what we did not find"), refs [13]-[20], two
matplotlib flowcharts (`docs/synopsis/build_figures.py`), and brief section 10 (search log).
v3 is now 4 pages (checked via Word PDF export).

**Follow-up 2 (same day):** user asked to remove the timeline, add Rishab Rathi as a 4th
member, make the terms understandable, and directly answer the professor's questions "how
would you verify the summary is correct" and "fine-tune or better prompts". Output is now
`VidhanAI_Synopsis_Report_v4.docx` (v3 was locked open in the user's Word, so v4 was written
beside it; the build script is still named `build_synopsis_v3.py`). Changes: timeline section
removed; 4-person rotating matrix (4 components x build/experiment/final phases, cyclic
shift; role assignments are MY default, not the team's decision); new section 1.4 (5-step
verification + how the checker itself is tested), new section 1.5 (setups A-E + explicit
decision rule), old jargon-heavy experiment diagram replaced by fig2_verify_decide.png; ladder
L0-L7 in the brief is condensed to 5 setups in the synopsis. Added `docs/PLAIN_ENGLISH_GUIDE.md`
(not for submission). FLAG: the handout says projects suit teams of 2-3; a team of 4 needs the
professor's OK.

**Unresolved:** v3/v4 are uncommitted (no commit requested). Team must rewrite/own the text,
fix D3 and T4, and start the P0 work in the synopsis timeline. Phase-2 date (3rd/4th week
of October) needs confirming with the faculty.

---

## 2026-09-18 — Session: course synopsis doc + rubric evaluation

**Intended:** Read `agentic_req.md` and the FinTrace example docx, evaluate
VidhanAI against the Agentic AI course rubric (Chapters 1–4, MAS/observability/
architecture requirements), then write the 3-section synopsis Word doc
(abstract + methodology, project plan + division of work, individual
understanding) for the team: Priyanshu Sharma, Gurvinder Singh, Krishna
Srivastava.

**What happened:**
- Evaluated the project against the `agentic_req.md` rubric by reading code and
  live data, not just docs: orchestrator.py (CrewAI Researcher + 7 tools,
  ReAct LLM planner + deterministic fallback), ai_service.py (3 honest
  backends), models/db (140 bills w/ full text, 11 tables, 5 summaries,
  16 bill versions, 10 subscriptions), ChromaDB (0 embeddings — collection
  missing), metrics_summary.json (n=5, bootstrap CIs), LoRA adapter (97.3 MB,
  392 tensors, 24,313,856 trainable params = 0.76% of 3.2B).
- Built `VidhanAI_Synopsis_Report.docx` (spec: `synopsis_spec.json`) following
  the FinTrace example's structure: Section 1 abstract + methodology,
  Section 2 plan + division of work (phase plan, rubric-coverage table,
  member split), Section 3 individual understanding per member
  (Priyanshu = architecture/orchestration/messaging, Gurvinder = RAG/data,
  Krishna = LLM/prompting/evaluation). Validated: ok, 52 blocks, 3 tables.
- Every number in the doc is from verified tool output (safetensors header
  parse, sqlite counts, metrics_summary.json) — nothing fabricated.

**Unresolved / next session should know:**
- After review, the user asked for a MUCH simpler doc: only project idea,
  summary, and goal (what we are working on, not accomplishments), no AI-look
  (no blue headings, no filler). Rewrote `VidhanAI_Synopsis_Report.docx` in
  place: 18 blocks, plain black headings, no tables, no metrics. The big
  evaluation content lives in git history and SESSION_LOG notes below.
- Rubric gaps called out earlier (ChromaDB unpopulated (T4), no LLM-as-Judge
  rubric, no 40+ run ledger, no MCP/A2A protocol, no hierarchical variant)
  remain Phase 4 work.
- Team members per the user: Priyanshu Sharma, Gurvinder Singh, Krishna
  Srivastava (the old proposal docx also lists Harsh Yadav — user's list wins).
- `synopsis_spec.json` kept in repo root for regenerating the docx.

---

## 2026-09-18 — Session: CLAUDE.md replacement + coordination files

**Intended:** Replace `CLAUDE.md` with the new generic "Hermes Agent — Project
Instructions" instruction set; create `TASKS.md` and `SESSION_LOG.md`.

**What happened:**
- `CLAUDE.md` replaced: the old VidhanAI session instructions are superseded by
  the new template (Project Snapshot, session startup routine, professionalism,
  git/PR best practices, cross-session coordination, tool permissions, coding
  standards). The old content is recoverable from git history — it was tracked
  and committed through `31b35cf`; the replacement is NOT committed yet.
- Created `TASKS.md` (task ledger; carries over the old §6 roadmap state as
  TODO/Done rows) and `SESSION_LOG.md` (this file).
- Filled in the new CLAUDE.md §1 snapshot (VidhanAI purpose/stack/URL/owner)
  and §7 coding standards (oxlint frontend, build/py_compile verification,
  run commands, error-envelope convention) from verified repo state — T1 done.
- Revised the CLAUDE.md git-commit policy to standard best practice: small
  atomic commits (one logical change each) with an explanatory body and
  intentional staging. The carried-over "one commit per phase" rule was
  removed — it contradicted atomic commits.

**Unresolved / next session should know:**
- The old CLAUDE.md contained project-specific truth the new template does NOT:
  repo map, how to run backend (:5000) / frontend (:5173), the API surface
  table, Windows/PowerShell notes, "never fabricate model results" honesty rule,
  commit-at-phase-boundary requirement, and the remote
  `https://github.com/DEATHGATE01/VidhanAi` (branch `main`).
- TODO T2–T4 carried from the old §6 roadmap (security review, Gmail OAuth2
  reconnect, ChromaDB vectorize, dead-artifact cleanup T5) — details in TASKS.md.

**Next session should start by:** reading the new `CLAUDE.md`, then TASKS.md,
then confirming `git status` (CLAUDE.md, TASKS.md, SESSION_LOG.md are currently
uncommitted changes on `main`).
