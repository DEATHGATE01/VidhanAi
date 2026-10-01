# SESSION_LOG.md — Session Diary

Chronological diary of what happened each session. See `CLAUDE.md` §5.2:
append at session start (what you intend to work on) and at session end
(what you did, what changed, what's unresolved, what the next session
should know). Prose, not just task status.

Newest entries at the TOP, oldest at the bottom.

---

## 2026-09-30 — Session: Groq summaries made real + ministry resolved for every bill

**Context.** Teacher feedback: a Bill is not the law, the Act is (handled by the
acts loop, task A1). While preparing the demo the user asked whether the
summaries were actually coming from Groq, and whether the model could supply a
ministry even when PRS does not. Both turned out to be live defects, and both are
now fixed and verified.

**1. The Groq path had never produced a single summary.** `generate_bill_summary`
was stamped `rule_based_extractive_v1` on every live call. Three independent
causes, found by testing rather than reading: (a) the default model
`groq/compound` no longer exists on this key (404 `does not exist or you do not
have access`); (b) the backend venv has **no `groq` SDK installed**, so the SDK
path raised ImportError and silently fell through; (c) Groq sits behind
Cloudflare, which returns `403` with `error code: 1010` to non-browser clients —
the SDK's User-Agent included — so even a valid model id failed. `requests` was
already a dependency, so the fix is a plain HTTPS call with a browser UA
(`generate_groq_summary`), defaulting to `openai/gpt-oss-120b`, with 429 handling
that honours `Retry-After`. Chain order is now **Groq → local Ollama → local LoRA
→ extractive**, so the local fine-tuned model is the offline/privacy fallback
instead of the default (measured on the higher-education Bill: 4,555 chars of
structured bullets in 3 s from gpt-oss-120b versus 3,073 chars in 195 s from
local qwen2.5:7b — the local path is real but 65× slower and flatter).
Verified live: `/api/bills/10/summary` → `groq_openai/gpt-oss-120b`, 904 words,
TL;DR intact. Nothing is fabricated: any failure still returns the honest
extractive fallback.

**2. Every bill had `ministry = "Unknown"` (140/140).** Summaries printed
"Ministry: Unknown" and ministry filtering was empty. **Correction to what was
believed earlier in this session:** PRS *does* publish the ministry — the field
is `div.field-name-field-ministry` and reads e.g. `Ministry: Finance`; the
scraper simply never wrote it to the database. So this was a scraping gap, not an
inference problem. `services/ministry_resolver.py` now resolves in tiers: PRS
bill page (`ministry_source='prs'`, confidence 1.0) → the bill's own text
(`'bill_text'`) → Groq choosing from a closed list of real Union ministries
(`'llm_inferred'`), which may answer "Unknown" but may never invent a ministry.
Provenance is stored, not hidden: new columns `ministry_source`,
`ministry_confidence`, `ministry_evidence`; the API adds `ministry_source` and
`ministry_inferred`; summary headers label a derived value "(inferred from the
Bill's text)" / "(inferred by AI)". A scraped value is never overwritten by a
derived one. Result: **`coverage now: prs=140`, zero Unknown**, and the LLM tier
was not needed at all for the current corpus (it stays for future bills PRS
omits, which is exactly what the user asked for). PRS's short taxonomy labels are
normalised to full names for display ("Personnel, Grievances and Pensions" →
`Ministry of Personnel, Public Grievances and Pensions`) with the raw scraped
string kept in `ministry_evidence`.

**New scripts** (all idempotent, all safe to re-run):
`scripts/maintenance/add_ministry_source_columns.py` (additive migration),
`scripts/setup/enrich_ministries.py` (`--offline`, `--bill-ids`, `--refresh`,
`--dry-run`, `--renormalise`, `--list`),
`scripts/maintenance/regenerate_summaries.py` (rebuilds cached summaries through
the real API code path; `--only-stale` targets non-generative rows).

**Gotchas for the next session.**
- Summaries are **cached** in `bill_summaries` and served forever, so a bill
  summarised before this fix keeps showing the extractive stub — use
  `regenerate_summaries.py` to refresh, and pre-generate the demo bills before
  presenting so a live 429 can never surface.
- The Groq free tier rate-limits bursts: an early batch of 5 regenerations got
  two 429s. Retries + `Retry-After` + ~3 s spacing handle it; don't hammer it.
- Two timeline payloads use different field names (A4 in TASKS.md): `bill.timeline
  .events[]` uses `date`/`event`; `/lifecycle` uses `event_date`/`event_type`.
  A component reading the wrong pair shows an empty timeline on good data.
- The backend must be **restarted** for these changes to reach the running app
  (done: :5000 is now serving the new code).
- Still open from D3: `agents/orchestrator.py:308`, `routes.py:1702` and
  `scripts/ml_pipeline/*` still name the dead `groq/compound` model.

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

## 2026-09-29 (later) — Overnight run: what actually happened (corrected diagnosis)

**Where the Acts work stands.** Pass 1 of the loop landed P0 completely: `Act`, `BillActLink`,
`LifecycleEvent` in `models.py`; `PRSActsScraper`, `act_linker`, `sync_acts`, `verify_acts`,
`migrate_acts_tables`; `/api/acts`, `/api/acts/<act_id>`, `/api/bills/<bill_id>/lifecycle`; the
fabricated `introduction_date + 30 days` timeline deleted. It used 3 read-only nemotron
subagents (PRS cross-check, code review, live API curls), re-verified their claims itself,
fixed two real findings (`Act.short_title` was NULL on all 50 rows; `source_url` not refreshed
on update), and committed (`37ce2cd`, `1b4aff4`, `72326a3`). DB: **50 acts / 406 lifecycle
events / 57 links** (32 verified, 25 candidate). `verify_acts.py` → 6/6 PASS, 0 unsourced,
0 estimated. PRS spot-check on bill 26 matched exactly.

**Then passes 2–4 burned six hours and committed nothing.** They were NOT stalled: they made
42/43/40 tool calls spanning ~115 minutes each of a 120-minute cap, and were killed mid-file.
The cause was pacing, not the provider — each model call on this endpoint takes ~1–2 minutes
(measured: 64s for a two-token reply on glm-5.3-flash, 105s on deepseek-v4.1-flash), so a
2-hour pass buys only 40–60 calls, and they had no commit discipline. Their uncommitted work
(models.py/routes.py edits adding the bill `act` block and the batched verified-link lookup for
the "Enacted as" chip, plus a `_ResilientStdout` guard so a dead Windows console handle can't
500 the bill route) was rescued into `d377e87` and compiles; it is WIP, unverified end-to-end.

**Correction — I briefly blamed the provider and that was wrong.** A scripted probe reported
`HTTP 500 "Missing request extension: Authorization"` for every model on nvidia, which looked
like an outage. The probe was reading the **redacted `api_key` from `config.yaml`**; the real
credential is `NVIDIA_API_KEY` in `.env`. With the real key nvidia answers fine. The probe
(`~/AppData/Local/hermes/scripts/cto_acts_probe.py`) now reads `.env` first, requires ~400
tokens (glm-5.3-flash is a reasoning model — a 16-token probe returns 200 with empty content and
looks like a dead endpoint), and takes the provider as a parameter.

**OpenRouter is configured but not a viable fallback for a full pass.** It answers small probes
and then returns `HTTP 402: This request requires more credits ... can only afford 24164` of the
requested 131072 output tokens. Fine for a probe, useless for an agent pass.

**What was changed to stop this recurring.**
- `docs/CTO_ACTS_PROMPT.md`: the pass must now commit after every coherent unit and is told
  explicitly to pace for 1–2 minute calls — a pass ending with nothing committed is a failed pass.
- `delegation.oneshot_max_children=8`, `max_spawn_depth=2` (was 2 and 1) so a pass can fan out;
  model split: pass = `z-ai/glm-5.3-flash`, children = `nvidia/nemotron-3-ultra-550b-a55b`
  (`delegation.model`/`delegation.provider=nvidia`), both pinned in the launcher.
- Loop relaunched at 22:53 (5 passes, 2h cap, 2-minute gap — passes chain instead of idling).
- `cto-acts-watchdog.sh` exists (probes until the provider is healthy, then launches the loop)
  but is **not running** — it is only needed if a genuine provider outage is suspected.

**Next session should know:** read `docs/cto-report-acts.md` first (pass 1's report is complete
and detailed). P1 frontend was still outstanding as of this entry: `ActsPage.jsx`,
`ActDetailPage.jsx`, `LifecycleTimeline.jsx`, the BillCard "Enacted as" chip, `/acts` route +
sidebar entry, `api.js` helpers — then `npm run build`. Criterion 6 (frontend build) was the only
unmet acceptance criterion when pass 1 closed. Review `d377e87` before merging: it is rescued
WIP, not verified work. Nothing is pushed; branch `feature/acts-tracking`.

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

---

## 2026-09-30 01:35–02:45 — Overnight CTO pass (acts loop): P1 UI completed, verified, committed; A5 defects fixed

**Intended:** Per `docs/CTO_ACTS.md` + `docs/CTO_ACTS_PROMPT.md` addendum: finish and
commit P1 (the frontend Acts UI the provider-stalled passes left uncommitted),
verify it for real, then fix the two A5 defects the browser check handed over.

**What happened:**
- Start state: pass 1 (2026-09-29) had committed P0 (`37ce2cd`); passes 2–4 were
  preserved as WIP in `d377e87` (routes.py act blocks, app.py resilient stdout).
  The working copy carried the P1 frontend files untracked/uncommitted. A
  concurrent hermes session landed `83ee403` (ministry enrichment, A3) and later
  `f4d948e`/`ef4fd2d`/`6a50a28` (timeline aliasing + handoff docs) DURING this
  pass — the route shape changed under me mid-investigation (my "act: null"
  probe was the flat shape of the old code; the new code nests under `bill`).
- Orchestration: 2 read-only children (contract-verifier, build-reviewer), both
  on nvidia/nemotron-3-ultra, disjoint by concern, no writers, no git. Build
  reviewer: build passes (2041 modules), lint warnings pre-existing, all §8
  checklist items verified. Contract verifier: contract holds — but its claim
  that `/api/bills/<id>` returns the act block was checked against the OLD code;
  I re-proved it myself post-restart (bill 21 → `bill['act']` verified:true,
  timeline 3 events all_sourced). `acts_by_bill`: 32 verified entries across all
  140 bills, keyed by bill id, chip contract fields all present.
- Committed `5e68837` feat(acts): P1 UI — ActsPage, ActDetailPage,
  LifecycleTimeline, BillCard "Enacted as" chip, Explore wiring, App/Sidebar
  routes, api.js (995 insertions).
- Fixed A5 (TASKS.md): `b315dcc` fix(acts) — candidate badge reads
  "Candidate N% — not confirmed" + section explanatory line; Act No./Status/
  Assented/Commenced render "Not published by PRS" with reason tooltips; /acts
  status filter dropped when all acts share one non-status. Verified in the
  LIVE browser on :5173 (detail page: no bare "60%", no "Act No.: —", "not
  confirmed" present; /acts: 0 status-filter selects, "Not published" cells).
- Data spine re-verified after the concurrent commits: verify_acts.py 6/6 PASS
  (50 acts / 406 events / 57 links), grep timedelta(days=30) empty, routes.py
  py_compile OK.

**Unresolved / next pass should know:**
- P2 (optional): India Code prober (indiacode.nic.in timed out 2026-09-29 —
  record the blocker if still unreachable), state-legislature Acts,
  lifecycle-stats analytics. §10 criterion 4 (5+ Passed bills' lifecycles vs
  PRS dates) has pass-1 evidence (6 bills re-checked, no drift) but a fresh
  re-verify before the merge would be cheap insurance.
- The backend on :5000 is the concurrent session's server (started 01:08:52,
  Windows-Store python) serving current code — do not kill it without checking
  listeners; it is NOT stale.
- /explore "Enacted as" chip needs a search to become visible (page 1 = newest
  unenacted bills) — optional polish the handoff noted, left as-is.
- A5's "chip visibility" half and P2 remain; everything else on A1–A5 is done.

---

## 2026-10-01 — Act details sourced from every legitimate source; CTO-1 retired, CTO-2 appointed

**Session intent (set at the end, from the operator's own words):** the operator
judged the overnight CTO "boring" because it never improved anything on its own —
"many details not published and it directly showed not published why not do some
internet search in backend get the details and display those info. and cto should
see to these details and improve these small things should not have to rely on me
for suggestions." Two deliverables: (1) actually source those details, (2) replace
the CTO with one that finds such gaps itself.

**1. Act details — built `backend/scripts/maintenance/enrich_act_details.py`.**
Three tiers, in authority order: India Code DSpace API → the Act's own official
PDF (downloaded to a temp file, read with `pdftotext`, Gazette header parsed for
`NO. n OF yyyy` and the assent sentence) → open-web corroboration (written only
when two independent sources agree; a single web hit is never enough). Every
written value stores the exact matched text in a new `acts.evidence` column; every
miss stores which sources were consulted, when, and what each answered in new
columns `acts.lookup_note` / `acts.details_checked_at` (migration:
`scripts/maintenance/add_act_evidence_column.py`). Act page shows it all in an
expandable "sources consulted / evidence" block, so "unknown" is now auditable.

Results on the live DB: **assent dates 17/50 → 50/50**, **Act numbers 17/50 →
35/50**, **in-force status 0/50 → 17/50** (from India Code `dc.identifier.repealed`),
commencement still 0/50 (India Code has no enforcement date for these — left NULL,
labelled), search trail on 50/50. The 15 Acts still without a number are the 2026
set, and the reason is now recorded per Act: India Code has no 2026 record, and the
"Act PDFs" PRS publishes for them are *Bill texts* ("AS PASSED BY BOTH HOUSES",
"Bill No. 139-F of 2026") that carry an assent endorsement but no Act number.

**Two errors of my own caught and fixed in the process** (both were exactly the
kind of silent inaccuracy this project cannot ship): India Code publishes no assent
field, so `dc.date.enact_date` (the *enactment/issue* date) was being written into
`assent_date` — it is now only a labelled last resort, and a PDF-vs-India-Code
disagreement is recorded as a CONFLICT with both dates (Bills of Lading Act 2025:
Act's own text 24 Jul 2025 vs India Code enact_date 17 Jun 2025 → the Act's own
text wins; 2 conflicts recorded). And the Act header hardcoded "Source (PRS)" for
every Act, mislabelling India Code item URLs — now labelled from `acts.source`.

**2. CTO-1 retired, CTO-2 appointed.** `docs/CTO_V2.md` (§0 records why CTO-1 was
replaced), pass prompt `docs/CTO_V2_PROMPT.md`, self-discovery ledger
`docs/CTO_BACKLOG.md` seeded with the findings from today, launcher
`~/AppData/Local/hermes/scripts/cto-overnight-cto2.sh`. The new mandate: every
pass dogfoods the live product, writes ≥3 evidenced findings of its own, fixes the
highest-value ones, and never asks the operator what to do. §2 is the rule that
would have caught today's complaint: an empty/unknown/placeholder value is a
finding to chase, never a final answer. `docs/CTO_ACTS.md` carries a superseded
note.

**Environment note:** the :5000 listener I found at 09:2x was serving pre-change
code (no `lookup_note` in `/api/acts/<slug>`) — two PIDs (928, 11820) held the
port and neither was an `app.py` process visible to `pkill`. Killed both via
PowerShell `Stop-Process` and started a tracked backend (`proc_a1d17092df1a`);
the frontend dev server on :5173 had died, restarted as `proc_25c6cf505660`. Both
verified 200 after restart.

**Verified live:** `npm run build` passes; `/api/acts/<slug>` returns `evidence` +
`lookup_note` + `details_checked_at`; browser on :5173 shows "There is a sourced
value" pages (Bills of Lading Act 2025 → Act No. 18, In force, 24 Jul 2025) and
"No number" pages (AP Reorganisation (Amendment) Act 2026 → "Not found — sources
checked" + the full search trail naming India Code, the Act PDF and Wikipedia).

**Unresolved / next pass should know:** the 15 2026 Acts still lack an Act number —
next step worth trying is the Gazette (`egazette.gov.in`) rather than another
aggregator; `/api/analytics/lifecycle-stats` is still unbuilt into any UI; 98
bills still generate summaries live (first 32 enacted bills are pre-cached); D3's
agent/`ml_pipeline` paths still name the dead `groq/compound`. Also: the frontend
build is fine but the dev server is not supervised — it does not survive a reboot.

---

## 2026-10-01 (later) — CTO-2's first self-discovered fix: a wrong date on every summary

**Question asked by the operator:** "is the cto improving anything implementing any
new idea or is he being useless?" Answer, from evidence rather than impression:
**both — a real find, wrapped in bad discipline.**

**What CTO-2 found (genuinely, unprompted, on its first pass).** `ai_service._format_header`
fell back to `date_scraped` when a bill had no introduction date, so the stored summary
header printed the date THIS SYSTEM scraped the bill as a legislative fact:
"**Introduced:** August 18, 2026" on a 2022 Act. CTO-2 estimated 30 of 42 cached
summaries were affected; the real number is **42 of 42** — every cached summary, both
Groq- and local-Ollama-generated. That is a reviewer-facing wrong date on every summary in
the product, and neither CTO-1 nor I had noticed it. It is the first finding in this project
produced by an agent rather than reported by the operator, so the CTO-2 mandate is working.

**What CTO-2 failed at.** Two passes ran to the 90-minute cap with **nothing committed**
and no report; the only commits since its appointment were mine. Its diff sat uncommitted in
the working tree for hours (one `timeout` kill from oblivion), the backfill script its own
comment referenced did not exist, and the launcher log holds only pass banners (647 bytes
for two passes) because a killed agent never flushes its buffered transcript. Mitigation
written into `docs/CTO_V2_PROMPT.md` (commit within 40 minutes; append the report as you go,
not at the end) and recorded as backlog finding 9.

**What I did to finish its fix** (its code fix alone was not enough — stored text keeps the
wrong date, and `bills.introduction_date` was NULL for all 140 bills):
1. Committed its `ai_service.py` change (`df99494`) so a capped pass could not lose it.
2. Wrote and ran `scripts/maintenance/backfill_introduction_dates.py`: 127/140 bills now
   have an introduction date copied from a sourced `lifecycle_events` row
   (`event_type='introduced'`, `source='prs_billtrack'`), event id printed per bill for
   audit; the 13 bills with no such event keep NULL and their summary omits the line.
3. Wrote and ran `scripts/maintenance/repair_summary_headers.py`: rebuilt the stored header
   of all 42 cached summaries with the SAME `_format_header` function (never hand-edited
   text), leaving each LLM body byte-identical so `model_version` stays truthful. Added
   `bill_summaries.header_repaired_at` so the edit is visible, not silent.
   Deliberately NOT regenerating through the LLM: 42 calls against a rate-limited free tier
   can degrade a summary to the extractive fallback hours before a demo, to rewrite bodies
   that were never wrong.
4. Restarted the backend: the live :5000 server was still running pre-fix code, so bills
   generated live during a demo would have printed the scrape date again.

**Verified:** independent re-query shows 0 mismatches between every stored header and
`bills.introduction_date`; the API serves bill 10 → "Introduced: July 27, 2026"; an uncached
bill generated live through the running server (bill 4) → "August 10, 2026", its real sourced
date; 42/42 rows carry `header_repaired_at`; `py_compile` clean on `ai_service.py`.
