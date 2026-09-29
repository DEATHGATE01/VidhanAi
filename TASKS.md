# TASKS.md — Task Ledger

Cross-session task ledger for this repo. See `CLAUDE.md` §5 for the rules:
mark a task `IN_PROGRESS` with the files you'll touch *before* editing; scan
for colliding `IN_PROGRESS` tasks first; on finish mark `DONE` or `BLOCKED`
with a reason. Never delete old tasks — move them to the Done section.

Last updated: 2026-09-18

---

## Active

| ID | Title | Status | Owner/Session | Files touched | Last updated |
|----|-------|--------|---------------|---------------|--------------|
| A1 | **Acts tracking:** plan Bill→Act lifecycle work after review feedback ("a Bill is not the law; the Act is"). Plan at `docs/ACTS_TRACKING_PLAN.md` (data model: `acts`, `bill_act_links`, `lifecycle_events`; PRS re-con verified: `/acts/parliament`, `/billtrack/category/billtrack`, per-bill status timeline selectors). Charter `docs/CTO_ACTS.md` (incl. orchestration rules + model split: pass = `z-ai/glm-5.3-flash` pinned in the launcher, children = `nvidia/nemotron-3-ultra-550b-a55b` via `delegation.model`; `delegation.oneshot_max_children=8`, `max_spawn_depth=2`) + pass prompt `docs/CTO_ACTS_PROMPT.md`; overnight loop on branch `feature/acts-tracking`. | IN_PROGRESS (P0 committed and verified; P1 frontend next) | hermes-session 2026-09-29 → overnight CTO loop | docs/ACTS_TRACKING_PLAN.md, docs/CTO_ACTS.md, docs/CTO_ACTS_PROMPT.md, docs/cto-report-acts.md, backend/models.py, backend/routes.py, backend/src/scraping/prs_acts_scraper.py, backend/services/act_linker.py, backend/scripts/setup/sync_acts.py, backend/scripts/maintenance/migrate_acts_tables.py, backend/scripts/verify_acts.py, frontend_new/src | 2026-09-29 |
| A2 | **Remove the fabricated bill timeline** (`backend/routes.py:262-327`: "passed" = introduction + 30 days, withdrawn/lapsed = `utcnow()`). Part of A1 P0 — lifecycle events must be sourced or absent. | DONE (verified: grep timedelta(days=30) over backend .py files returns empty; get_bill timeline reads only sourced LifecycleEvent rows; see docs/cto-report-acts.md pass 1) | overnight CTO loop | backend/routes.py | 2026-09-29 |
| A3 | **Ministry enrichment for every bill.** All 140 bills read `ministry = "Unknown"`, so summaries printed "Ministry: Unknown" and ministry analytics were empty. Fixed: `services/ministry_resolver.py` resolves in tiers — PRS bill-page field (`ministry_source='prs'`, conf 1.0) → the bill's own text → Groq choosing from a closed list of real Union ministries, never inventing one. Provenance columns `ministry_source`/`ministry_confidence`/`ministry_evidence` added to `bills`; API exposes `ministry_source` + `ministry_inferred`; summary headers label inferred values. **Correction to the earlier diagnosis:** PRS *does* publish the ministry (field `field-name-field-ministry`); the scraper simply never wrote it, so no inference was needed in the end. | DONE (verified: `coverage now: prs=140`, 0 unknown; bill 10 → `Ministry of Personnel, Public Grievances and Pensions`, source `prs`, `ministry_inferred: false`) | hermes-session 2026-09-30 | backend/services/ministry_resolver.py (new), backend/scripts/setup/enrich_ministries.py (new), backend/scripts/maintenance/add_ministry_source_columns.py (new), backend/models.py, backend/ai_service.py, backend/routes.py | 2026-09-30 |
| A4 | **Timeline payload field names must be handled by the P1 frontend.** Two endpoints return the same events with different keys — `GET /api/bills/<id>` → `bill.timeline.events[]` with `date`/`event`, and `GET /api/bills/<id>/lifecycle` → top-level `events[]` with `event_date`/`event_type`/`house` + `all_sourced`. A component that reads the wrong pair renders an empty timeline on correct data. | DONE (fixed at the source rather than left as a trap: both payloads now emit both spellings plus `house`, and `bill.timeline` carries `all_sourced`/`event_count`. Verified live: `bill.timeline.events[0]` keys = `['date','event','event_date','event_type','house','is_estimated','notes','source','source_url','title']`, `all_sourced: true`, `event_count: 3`; `/lifecycle` = 4 events, both spellings) | hermes-session 2026-09-30 | backend/routes.py, frontend_new/src/components/LifecycleTimeline.jsx | 2026-09-30 |
| A5 | **Acts UI: unverified matches read as confirmed; empty fields look broken.** Browser check 2026-09-30 01:30: `/acts/<act>` lists a 60% *candidate* link in the same "Bills This Came From" section as the verified one (only a bare "60%" distinguishes them), and Act No./Assented/Commenced render `—` while Status renders `unknown` — values PRS genuinely does not publish, so they must be labelled, not invented. Also `/explore` page 1 shows only unenacted newest bills, so the "Enacted as" chip is invisible until you search. | TODO (handed to the overnight CTO pass; see "Addendum — 01:35" in docs/CTO_ACTS_PROMPT.md) | overnight CTO loop | frontend_new/src/pages/ActDetailPage.jsx, frontend_new/src/pages/ActsPage.jsx, frontend_new/src/pages/ExplorePage.jsx | 2026-09-30 |
| D2 | Rebuild synopsis after 5/10 feedback: research agent entropy, summarization evaluation/verification, architecture, prompting-vs-FT with verified citations; align to handout Phase-1 rubric (C2-C5). **Drafted:** v3.docx + docs/RESEARCH_BRIEF.md + docs/synopsis/build_synopsis_v3.py. Awaiting team review/rewrite in their own words; Section 3 left to each member. | BLOCKED (needs team review) | hermes-session 2026-09-21 | VidhanAI_Synopsis_Report_v4.docx (supersedes v3), docs/RESEARCH_BRIEF.md, docs/PLAIN_ENGLISH_GUIDE.md, docs/synopsis/build_synopsis_v3.py, docs/synopsis/build_figures.py (+ 2 PNG figures), SESSION_LOG.md, TASKS.md | 2026-09-21 |

---

## TODO

| ID | Title | Status | Owner/Session | Files touched | Last updated |
|----|-------|--------|---------------|---------------|--------------|
| D3 | **URGENT:** `groq/compound` was shut down by Groq on 2026-09-21 (no replacement listed; requests now error). Default is set in `backend/ai_service.py:112`, `scripts/ml_pipeline/*`, and hard-coded in `backend/agents/orchestrator.py:308` + `routes.py:1408`. Repoint to a pinned model (candidates on Groq's models page: `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`) and re-test the LLM-agent and summary paths. **Summary path FIXED 2026-09-30** — three independent causes were found, not one: (1) the model id was dead, (2) the deploy venv has no `groq` SDK so the SDK path silently degraded, (3) Groq's Cloudflare edge returns `403 error code 1010` for non-browser clients, so even a valid model id failed. `generate_groq_summary` now calls the REST API over HTTPS with a browser UA, defaults to `openai/gpt-oss-120b`, and absorbs 429s using `Retry-After`. Verified live: `/api/bills/10/summary` → `groq_openai/gpt-oss-120b`. **Still TODO:** `agents/orchestrator.py:308` (`groq/groq/compound`), `routes.py:1702`, `scripts/ml_pipeline/1_generate_dataset.py` + `3_calculate_metrics.py` still name the dead model, and stale docstrings in `ai_service.py`. | IN_PROGRESS (summary path DONE; agent + metrics paths remain) | hermes-session 2026-09-30 | backend/ai_service.py, backend/agents/orchestrator.py, backend/routes.py, backend/scripts/ml_pipeline/ | 2026-09-30 |
| T2 | Run a security review over the new frontend code (XSS in rendered narratives, localStorage session handling in `vidhanai-user`) | TODO | — | frontend_new/src | 2026-09-18 |
| T3 | Reconnect the n8n "Gmail account" OAuth2 credential (token expired/revoked) so alert subscriptions deliver real email | TODO | — (user action in n8n UI) | n8n credentials only | 2026-09-18 |
| T4 | Vectorize documents into ChromaDB (`backend/scripts/ml_pipeline/2_vectorize_docs.py`) — collection `legal_bills` missing, semantic search returns 0 results | TODO | — | backend/instance/chroma_db | 2026-09-18 |
| T5 | Delete `backend/db_service.py.bak` and empty dirs (`hooks/`, `components/ui/`); populate or remove half-artifacts | TODO | — | backend, frontend_new/src | 2026-09-18 |

---

## Done

| ID | Title | Status | Owner/Session | Files touched | Last updated |
|----|-------|--------|---------------|---------------|--------------|
| T0 | Create `TASKS.md` and `SESSION_LOG.md` per new CLAUDE.md instructions | DONE | hermes-session 2026-09-18 | TASKS.md, SESSION_LOG.md | 2026-09-18 |
| T1 | Fill in `CLAUDE.md` §1 Project Snapshot and §7 Coding Standards placeholders | DONE | hermes-session 2026-09-18 | CLAUDE.md | 2026-09-18 |
| A1–A7 | Phase A — Make frontend_new boot (router shell, Header, pages, BillCard, Vite proxy, title, build passes) | DONE | 2026-08-25 | frontend_new/ | 2026-08-25 |
| B1 | Repoint start.bat/start.ps1/vercel.json to frontend_new; README updated | DONE | 2026-09-01 | start.bat, start.ps1, vercel.json, README.md | 2026-09-01 |
| Phase D | Alerts workflow (backend + n8n + AlertsPage live; complete except T3 user action) | DONE | 2026-08-26 | models.py, routes.py, n8n-workflows/, frontend_new/src | 2026-08-26 |
| Phase E code | Ollama backend in ai_service.py + scripts/notebooks/Modelfile (remaining manual Kaggle/Ollama steps are user actions) | DONE | 2026-09-02 | backend/ai_service.py, backend/scripts/maintenance/regenerate_summaries_for_ft.py, notebooks/, backend/Modelfile.ollama | 2026-09-02 |
| FE-fix | Ask VidhanAI 502s + natural-language lookups resolved (reloader off by default, search_bills tokenized) | DONE | 2026-09-03 | backend/app.py, backend/db_service.py, frontend_new/src/services/api.js | 2026-09-03 |
| FE-fix | Frontend consolidation: Explore overlay, portal login, Architecture/Playground/Search pages removed | DONE | 2026-09-03 | frontend_new/src | 2026-09-03 |
| Demo | demo-tunnel.ps1 launcher for the public local-model URL | DONE | 2026-09-03 | demo-tunnel.ps1 | 2026-09-03 |
