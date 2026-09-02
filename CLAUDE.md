# VidhanAI — Session Instructions & Project Context

> **Read this first.** This file is the canonical onboarding doc for any Claude session
> working in this repo. It records what the project is, what state it is in right now,
> what is broken, and what to do next — so a fresh session can act immediately without
> re-discovering everything.

---

## 1. What this project is

**VidhanAI** is an academic/internship project: a Generative AI legislative
simplification engine for Indian parliamentary bills (data source: PRS India BillTrack).

Core claims (from the research paper):
- QLoRA fine-tuned Llama-3.2-3B for legal text simplification
- CrewAI multi-agent orchestration (7 specialist tools)
- ChromaDB semantic RAG (~12k embeddings, all-MiniLM-L6-v2)
- Delta-aware amendment summarization (the novel research contribution)
- Dual guardrails: input injection filter + output fact-checker
- $0/month deployment target (Render + Vercel free tiers)

**Stack:** Python/Flask backend · SQLite (11 tables) · ChromaDB · React 19 + Vite +
Tailwind CSS 4 frontend · Groq LLM API (`groq/compound`) · n8n workflows for alerts.

**Not a git repository.** There is no version history. Be careful with destructive edits.

---

## 2. Repository map

```
VidhanAi-main/
├── CLAUDE.md                  ← you are here (session instructions)
├── README.md                  ← public-facing overview (mostly accurate)
├── PHASE1_STATUS.md           ← reproducibility fixes record (local-only, gitignored)
├── PHASE2_STATUS.md           ← real QLoRA training plan (local-only, gitignored)
├── start.bat / start.ps1      ← Windows launchers (backend :5000 + frontend :3000)
├── render.yaml                ← Render.com deploy blueprint (backend)
├── vercel.json                ← Vercel deploy config (frontend)
├── backend/                   ← Flask REST API (MATURE, working)
│   ├── app.py                 ← create_app() factory; auto-creates schema; WAL mode
│   ├── routes.py              ← ALL API endpoints (see §4)
│   ├── models.py              ← 11-table SQLAlchemy schema (source of truth)
│   ├── db_service.py          ← data-access layer used by routes
│   ├── ai_service.py          ← LLM backends: groq_expert | local_lora | rule_based
│   ├── config.py              ← EMPTY (intentional placeholder; app.py reads env vars)
│   ├── agents/orchestrator.py ← CrewAI Researcher agent + 7 tools
│   ├── services/amendment_service.py ← pure-Python structural diff engine
│   ├── instance/regulation_alert.db  ← the SQLite database
│   ├── instance/chroma_db/    ← vector store
│   ├── scripts/
│   │   ├── setup/             ← seed_bills_for_ft.py, fetch_all_bill_data.py, ...
│   │   ├── ml_pipeline/       ← 1_generate_dataset.py, 2_vectorize_docs.py,
│   │   │                        3_calculate_metrics.py
│   │   └── maintenance/       ← seed_bill_versions.py, add_bill_status_column.py,
│   │                            clear_* cache scripts
│   ├── src/scraping/prs_billtrack_scraper.py
│   └── requirements.txt
├── frontend_new/              ← ✅ THE FRONTEND (React 19 + Vite 8 + Tailwind 4).
│                                 Fully working — see §5.
├── notebooks/
│   ├── qlora_finetuning.ipynb ← Kaggle T4×2 training notebook (paper's hyperparams)
│   └── roundtrip_lora.py      ← bundle dataset zip / extract adapter (rejects stubs)
├── n8n-workflows/             ← alert email automation JSON
└── docs/                      ← ARCHITECTURE.md, MODEL_COMPARISON.md, IEEE_Report.md
```

---

## 3. How to run things

### Backend (Flask, port 5000)

```powershell
cd backend
python app.py
# → http://127.0.0.1:5000  (API under /api, health at /api/health)
```

- Requires `backend/.env` with `GROQ_API_KEY=...` for summaries/research/narratives.
  Without it, the app boots and serves DB-backed endpoints but LLM features degrade
  to the extractive fallback (`rule_based_extractive_v1`).
- DB path override: `VIDHANAI_DB_PATH`. CORS origins override: `VIDHANAI_CORS_ORIGINS`
  (defaults allow localhost:3000 and localhost:5173).
- `backend/config.py` is intentionally empty — configuration lives in `app.py` +
  environment variables. Don't "fix" this without a reason.

### Frontend (Vite, port 5173)

```powershell
cd frontend_new
npm install        # if node_modules missing
npm run dev        # → http://localhost:5173
```

✅ **Fixed 2026-08-25** — `npm run dev` and `npm run build` both pass; verify with
`npm run build` after any frontend change.

### Full-stack smoke test

```powershell
# Terminal 1
cd backend; python app.py
# Terminal 2
cd frontend_new; npm run dev
# Terminal 3 — sanity:
curl http://127.0.0.1:5000/api/health
curl "http://127.0.0.1:5000/api/bills?page=1&per_page=3"
```

---

## 4. Backend API surface (routes.py — verified)

All endpoints are prefixed `/api`. Response envelope: `{success, ...}` or `{error}`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Health check |
| `/search?keyword=` | GET | Keyword search (SQL LIKE) |
| `/semantic-search?query=` | GET | ChromaDB vector search + input guardrails |
| `/bills?page=&per_page=&ministry=&status=` | GET | Paginated bill list |
| `/bills/<bill_id>` | GET | Bill detail + sentiment + timeline + linked news |
| `/bills/<bill_id>/summary` | GET | AI summary (auto-generates & caches) |
| `/bills/<bill_id>/versions?limit=` | GET | BillVersion snapshot history |
| `/bills/<bill_id>/news?limit=` | GET | Google News RSS citations |
| `/users/register` | POST | Register (email, username, password) |
| `/users/<id>` | GET | Profile |
| `/users/<id>/analytics` | GET | Behavior analytics |
| `/users/<id>/favorites` | GET/POST | Favorites CRUD (DELETE via `/favorites/<fid>`) |
| `/users/<id>/history` | GET | Reading history |
| `/users/<id>/history/<bill_id>` | PUT | Update time-spent/scroll-depth |
| `/users/<id>/searches` | GET | Search history |
| `/analytics/trending` | GET | Trending searches |
| `/analytics/ministry` | GET | Bills per ministry |
| `/analytics/heatmap` | GET | Reading heatmap |
| `/analytics/stats` | GET | DB-wide statistics |
| `/subscribe` | POST | Alert subscription (n8n integration) |
| `/unsubscribe` | POST | Deactivate subscription |
| `/check-new-bills` | POST | Called by n8n cron; returns alerts to email |
| `/notifications/<id>/sent` | POST | n8n marks email sent |
| `/subscriptions` | GET | Admin listing |
| `/agent/research` | POST | CrewAI multi-agent research `{question, max_steps, use_llm_planner}` |
| `/architecture` | GET | Live service inventory JSON (feeds Architecture page) |
| `/amendment/diff` | POST | Delta diff `{bill_id_v1, bill_id_v2}` or raw texts |
| `/admin/index-all-bills` | POST | Re-scrape/index all PRS bills |

Notes:
- **No auth system exists.** Users are rows keyed by integer id; there is no login/JWT.
  Any frontend auth UI is cosmetic unless the team decides to add real auth.
- `use_llm_planner=true` on agent/research hits a known Groq request-size limit;
  default deterministic planner is the safe path.
- Summaries record `model_version`, `guardrail_applied`, `guardrail_version` for audit.

---

## 5. Frontend state — RESOLVED (2026-08-25)

All Phase-A defects are fixed and verified (`npm run build` passes; all 7 routes
clicked through against a live backend in Chrome):

- App.jsx rewritten as a clean router shell (single BrowserRouter from main.jsx,
  routes: `/`, `/explore`, `/research`, `/amendments`, `/architecture`,
  `/playground`, `/search`, `*` catch-all).
- Header/Footer rewritten (nav driven by `config/modules.js`; Footer social icons
  use Globe/MessageCircle/Mail — this lucide-react version dropped brand icons).
- All pages repaired or created: LandingPage, ExplorePage (derived filter/sort/
  pagination), ResearchPage (chat + agent-trace panel), BillCard +
  AdvancedFilters components, AmendmentsPage, ArchitecturePage, PlaygroundPage,
  SearchPage.
- Utility classes added to index.css `@layer utilities`: `.glass-panel`,
  `.premium-input`, `.chip`, `.spinner-ring`, `.bot-avatar`, `.chat-bubble(-user)`,
  `.trace-output`, keyframes `fade-in-up`/`pulse-glow`/`spin`.
- Tailwind v4 PostCSS plugin installed and configured (`@tailwindcss/postcss`
  replaced v3-style `tailwindcss` plugin in postcss.config.js). `axios` added to
  dependencies. Vite proxy `/api → http://127.0.0.1:5000` active. index.html title
  set to product name.
- Theme system (2026-08-31): light/dark mode with toggle. `src/context/ThemeContext.jsx`
  (`ThemeProvider`/`useTheme`) persists key `vidhanai-theme` in localStorage, respects
  `prefers-color-scheme` on first visit, and mirrors onto `<html data-theme>`.
  `index.html` carries an inline anti-FOUC script so reloads never flash the wrong mode.
  `src/components/ThemeToggle.jsx` (Sun/Moon) renders in the Sidebar desktop footer +
  mobile top bar. `index.css`: `:root` = clean white light tokens,
  `[data-theme="dark"]` = AMOLED black; all hardcoded dark-only colors swapped for
  semantic vars (`--ok`/`--danger`/`--warn`/`--info`/`--accent-2`/`--accent-3`/
  `--on-accent`/`--hover`/`--backdrop`/`--shadow-lg`/`--scrollbar`). Verified: `npm run
  build` passes; toggle round-trip, persistence + reload confirmed in Chrome.
- Mascot "Vid" (2026-08-31, revised 2026-09-02): a friendly AI bot with the scales of
  justice balanced on its head — two eyes + smile read as a character at a glance, the ⚖️
  signals law, and tiny arms + legs (each limb its own `<g>`). Body = LAVENDER orb with a
  4px accent-purple outline (light `--orb #ece4fc` / dark `#2a2447`; the outline +
  tint fix a "white blends into background" visibility bug), big sparkly eyes (11.5r +
  double highlights), rosy blush, wide smile. `src/components/Vid.jsx` is a theme-aware
  React SVG (expressions: cheerful/wink/curious; all shapes inlined so instances never
  collide). Movement is class-gated so small/logo instances stay still: `lively` = bob +
  right-arm wave (greeting, landing hero, empty states, answer byline); `walking` =
  swinging legs/arms + bob (the AI "searching" state); both disabled under
  `prefers-reduced-motion`. In the Ask VidhanAI greeting Vid is 112px standing on a
  blurred ground-shadow ellipse. Placed in: Landing hero, Ask VidhanAI
  greeting/processing/answer, Sidebar logo (mobile 24 / desktop 28), Explore + Search
  empty states (64px). Mascot tokens (`--orb`/`--orb-hi`/`--coat`/`--coat-collar`/
  `--gold`/`--eye`/`--blush`) in both themes. `public/favicon.svg` is the Vid mark
  (standalone colors, lavender orb + outline). `npm run build` passes; contrast verified
  in Chrome in both themes (orb vs canvas distinct, no console errors).
- "Ask VidhanAI" chat (2026-09-02): ResearchPage is an OPEN Brik-style workspace (no boxed
  chat panel): the page itself is the `--chat-bg` canvas (light #F5F7F6 / AMOLED #0a0a0a)
  with the lavender `--chat-glow` at upper-left, an IDLE → PROCESSING → RESULT state
  machine, and generous 2rem gutters. Header = "Ask VidhanAI" + subtitle + a pill-styled
  CrewAI LLM-planner toggle. IDLE: center-left greeting — 96px Vid (lively, standing on a
  blurred ground-shadow ellipse) + time-aware "Good morning, VidhanAI is ready for
  Parliament." + description. PROCESSING: query in a lavender right-aligned bubble, a
  4-stage progress pipeline (STAGES: Understanding → Searching PRS/ChromaDB →
  Cross-checking → Writing; advances every 2.6s), a contextual operation message, and a
  centered WALKING mascot on a ground shadow — no generic spinner; input disabled +
  suggestions hidden while running. RESULT: query bubble + a white answer card (Vid
  byline + agent text + source-URL citation chips). Right column (`.ask-kpi`, hidden on
  mobile, no divider) = "RIGHT NOW" + 3 KPI cards (958+ bills / 7 agents / 140+ full-text,
  static) + TODAY summary bar; persists across phases. Bottom = white pill input (purple
  border + glow, 18px radius) + solid indigo Ask button + 6 white suggestion chips.
  Agent-trace panel removed. Tokens `--chat-bg/--chat-glow/--chat-surface/--chat-card/
  --chat-input-bg/--shadow-sm` in both themes. `.ask-page` sizes the workspace
  (min-height `min(880px, calc(100dvh - 9.5rem))`, mobile override). `npm run build`
  passes; verified in Chrome (both themes; idle→processing→result; no console errors).
  NOTE: `/agent/research` intermittently 502s even with Flask up — the known
  dev-reloader flakiness; retry usually succeeds.
- Local fine-tuned model serving (2026-09-02): `backend/ai_service.py` gained an
  **Ollama backend** so the app can generate summaries with the QLoRA fine-tuned
  Llama-3.2-3B (served on the laptop's CPU) instead of Groq — see Phase E in §6
  for the env vars, new scripts, and the remaining manual (Kaggle/Ollama) steps.

Known non-frontend items discovered during verification:
1. **ChromaDB collection `legal_bills` does not exist** → semantic search always
   returns 0 results. Fix: run `backend/scripts/ml_pipeline/2_vectorize_docs.py`.
2. **Deterministic planner's `bill_lookup` keyword matching is weak** — natural
   questions like "What is X Bill 2023 about?" often miss; simple keywords work.
   Backend tuning item.
3. **First research request after backend boot can take ~60s+** (one-time PRS list
   fetch) and Flask dev-server watchdog reloads mid-request can yield proxy 502s.
   Subsequent requests are ~7s.

---

## 6. TODO / action roadmap

Do these in order. Each item lists *what* and *how*. Check off nothing silently —
verify each step compiles/runs before moving on.

### Phase A — Make frontend_new boot ✅ DONE (2026-08-25)

All items completed and verified — see §5 for the resolved-state summary and the
three non-frontend follow-ups discovered during verification.

- [x] **A1.** App.jsx rewritten as clean router shell
- [x] **A2.** Header.jsx fixed, nav driven by config/modules.js
- [x] **A3.** AmendmentsPage / ArchitecturePage / PlaygroundPage / SearchPage created
- [x] **A4.** BillCard + AdvancedFilters created (AdvancedFilters actually rendered)
- [x] **A5.** Vite proxy `/api → 127.0.0.1:5000` added
- [x] **A6.** index.html title set to VidhanAI
- [x] **A7.** `npm run build` passes; all routes smoke-tested in browser vs live API

### Phase D — Alerts workflow (IN PROGRESS, 2026-08-25)

**Done & verified:**
- `models.py`: `BillNotification.bill_status` column added; migration script
  `backend/scripts/maintenance/add_bill_status_column.py` (idempotent, already applied).
- `routes.py /subscribe`: returns `recent_matches` (top-3 recent bills matching
  keywords/ministries) for category subscriptions — verified.
- `routes.py /check-new-bills`: status-change detection for specifically-tracked
  bills (compares vs `bill_status` snapshot, updates the row in place to respect
  the unique(subscription_id,bill_id) constraint, sets `alert_type:'status_update'`,
  `previous_status`) — smoke-tested.
- `n8n-workflows/welcome-email-workflow.json`: VALID. Webhook
  `POST /webhook/vidhanai-welcome-email` → Code (builds HTML: bill summary cards
  for specific-bill subs, recent-matches table for category subs) → emailSend.
  Import into n8n, attach SMTP credential, set fromEmail, activate.

**Status (2026-08-26): Phase D COMPLETE except one user action.**
- Backend: bill_status migration applied; /subscribe returns recent_matches;
  /check-new-bills detects status changes — all verified.
- n8n: both workflows ACTIVE in local instance via API
  (welcome `yY2WTxmoBDpZ0nBE`, alerts `8dnHGcQOtaGoghdT`); Gmail OAuth2 nodes
  with credential pre-attached; hourly cron executing successfully.
- Frontend: AlertsPage live at /alerts (bill/topic tabs, keyword chips,
  ministry toggles, frequency cards) — fires the welcome webhook after
  /api/subscribe, res.ok-checked. Build passes; end-to-end subscribe tested
  in browser against live backend + n8n.

**The ONE remaining step is a user action:** the "Gmail account" OAuth2
credential's token is expired/revoked (execution 266 failed at Send email:
"authorization grant ... invalid, expired, revoked"). Reconnect it in
n8n → Settings → Credentials → Gmail account → Sign in again. After that,
subscribing at http://localhost:5173/alerts delivers real email.
2. Frontend AlertsPage: `AlertsPage.jsx` (tabs: Specific Bill / Category;
   email input; bill picker via `getAllBills`; keyword chips; ministry select;
   frequency instant/daily/weekly) → `POST /api/subscribe` → then POST the
   n8n webhook URL from `import.meta.env.VITE_N8N_WEBHOOK_URL` (skip if unset).
   Add `/alerts` route to App.jsx + `{id:'alerts', label:'Alerts', icon:Bell}`
   to `config/modules.js` (Header renders modules automatically).
3. Update `n8n-workflows/N8N_SUBSCRIPTION_GUIDE.md` — it references dead
   endpoints (`/api/subscriptions/subscribe`, `/api/bill_notifications`); the
   real ones are `/api/subscribe`, `/api/check-new-bills`,
   `/api/notifications/<id>/sent`.
4. Test end-to-end: subscribe via UI → welcome email; insert fake new bill →
   run check workflow → alert email; flip a tracked bill's status → status email.

### Phase E — Local fine-tuned model in the running app (IN PROGRESS, 2026-09-02)

**User decision:** the app's bill summaries must be produced by the locally
fine-tuned Llama-3.2-3B (not Groq) during the in-person demo; the public URL
(Vercel → Render) keeps Groq for the course's deploy requirement. Laptop =
Ryzen 7 5700U / 13.8 GB RAM / no NVIDIA GPU → the PyTorch `local_lora` path
can't run there; the working route is a **Q4 GGUF on CPU via Ollama**.

**Code done & verified (2026-09-02):**
- `backend/ai_service.py`: new **Ollama backend**. When `VIDHANAI_USE_OLLAMA=1`,
  summaries + amendment narratives are generated FIRST by the fine-tuned model and
  stamped `model_version = local_ollama_<model>`; TL;DR extraction routes through
  the same backend chain so a fine-tuned summary never triggers a hidden Groq call.
  Unset (public deploy) → unchanged `groq_compound`. New env vars:
  `VIDHANAI_OLLAMA_URL` (default `http://127.0.0.1:11434/v1`),
  `VIDHANAI_OLLAMA_MODEL` (default `vidhanai`), `VIDHANAI_OLLAMA_MAX_TOKENS`
  (default `384`). No new pip deps.
- `backend/scripts/maintenance/regenerate_summaries_for_ft.py` (NEW): deletes the
  cached `BillSummary` row for given bill ids (or `--all`), regenerates under the
  enabled backends, prints the resulting `model_version`/latency — needed because
  `get_or_generate_bill_summary` returns the cache and would otherwise mask the
  local model with an old Groq summary. Run with:
  `VIDHANAI_USE_OLLAMA=1 python scripts/maintenance/regenerate_summaries_for_ft.py <ids>`
- `notebooks/export_lora_to_gguf.ipynb` (NEW): one-time Kaggle free-T4 run — loads
  the adapter dir, merges, saves a Q4_K_M GGUF (~2 GB) for local Ollama.
- `notebooks/roundtrip_lora.py`: added `--bundle-adapter` (zips
  `notebooks/lora_model/` for Kaggle Dataset upload).
- `backend/Modelfile.ollama` (NEW): registers the GGUF as Ollama model `vidhanai`.
- Verified: `py_compile` clean on all changed files; with `VIDHANAI_USE_OLLAMA=1`
  and Ollama unreachable, summaries degrade to `rule_based_extractive_v1` with no
  Groq key and no hidden Groq call.

**Remaining MANUAL steps (need the user's laptop + Kaggle):**
1. `python notebooks/roundtrip_lora.py --bundle-adapter` → upload the zip to a
   new Kaggle Dataset.
2. Run `notebooks/export_lora_to_gguf.ipynb` on Kaggle → download the GGUF →
   rename to `vidhanai-lora-q4_k_m.gguf` under `D:\models\vidhanai\`.
3. Install Ollama (Windows, free) → fix the `FROM` path in
   `backend/Modelfile.ollama` → `ollama create vidhanai -f backend/Modelfile.ollama`.
4. Run backend with `VIDHANAI_USE_OLLAMA=1` and **no** `GROQ_API_KEY`; regenerate
   4–5 demo bills; confirm `local_ollama_vidhanai` stamps. First hit per bill is
   slow (~20–45 s on CPU), DB-cached afterwards — pre-warm the demo bills.
5. Public deploy needs **no code change**: root `vercel.json` already rewrites
   `/api` → `vidhanai-backend.onrender.com`; set `GROQ_API_KEY` + seed the DB on
   Render. Its summaries stay `groq_compound` — honest and sufficient for the
   course deploy requirement.

### Phase B — Consolidation & hygiene (after Phase A works)

- [x] **B1.** (2026-09-01) Repointed `start.bat`, `start.ps1`, and `vercel.json` to
      `frontend_new`; README quick-start + repo map updated to `frontend_new` / :5173.
      No `frontend/` stub exists on disk — `frontend_new` is the single frontend dir.
      `backend/app.py` CORS still lists the extra `:3000` origins (harmless superset).
- [ ] **B2.** Initialize git (`git init` + sensible `.gitignore` covering
      `node_modules/`, `backend/instance/*.db`, `backend/.env`, `__pycache__/`,
      `.ruff_cache/`, `notebooks/lora_model/adapter_model.safetensors`) and make an
      initial commit. The repo currently has ZERO version control — do this before
      any risky refactor.
- [ ] **B3.** `backend/db_service.py.bak` and empty dirs (`hooks/`, `components/ui/`)
      — delete or populate; don't leave half-artifacts.
- [ ] **B4.** Run a security review over new frontend code once it calls
      APIs (XSS in rendered narratives, localStorage token handling if auth ever lands).

### Phase C — Product depth (pick per demo needs; see PHASE1/PHASE2 docs)

- [ ] **C1.** Wire Favorites/History behind a lightweight "local profile" (store the
      registered `user_id` in localStorage after `/users/register`) — no password auth
      needed for a demo.
- [ ] **C2.** Alerts page → `/subscribe` flow (email + keywords + ministries),
      surfaced through n8n workflow.
- [ ] **C3.** Sentiment chart + timeline rendering on a bill-detail view (backend
      already returns `sentiment` and `timeline` on `/bills/<id>`).
- [ ] **C4.** ML track (separate from UI work): follow `PHASE2_STATUS.md` §"Run this
      in order" — seed ≥100 bills → generate dataset → Kaggle train → install real
      adapter → honest eval. Never fake metrics; `3_calculate_metrics.py` refuses to
      run without a ≥1 MB adapter by design.

---

## 7. Working agreements for this repo

1. **Never fabricate model results.** Phase 1 removed fake "fine-tuned" numbers;
   keep it that way. Metrics only from `3_calculate_metrics.py` with a real adapter,
   or explicitly labeled Groq fallback.
2. **Backend contract is stable** — prefer adapting frontend code to the API shapes in
   §4 rather than changing route responses casually.
3. **Windows environment.** PowerShell primary; use forward-slash-safe paths in
   scripts; the GateGuard hook requires stating facts before first Bash command.
4. **Style:** follow existing patterns — pages use hooks + lucide-react icons +
   Tailwind utility classes; backend uses blueprint + db_service layering.
5. When a task finishes, update THIS file (§5 defect list, §6 checkboxes) so the next
   session inherits truth, not archaeology.
6. **Commit at every phase boundary** (user requirement — resume-grade history):
   - Remote: `https://github.com/DEATHGATE01/VidhanAi` (branch `main`, HTTPS).
   - One conventional commit per completed PHASE (not per task, not one blob):
     `feat|fix|docs|chore|refactor(scope): summary` + body bullets describing
     what changed and why. Push to origin immediately after.
   - Stage by subsystem (`git add <paths>`), never blind `git add -A`.
   - Commit messages must carry context: what happened, why, and anything the
     next reader needs (e.g. "superseded by X", "regenerable via Y").
   - Keep the repo clean & professional: delete dead code/empty dirs/stale
     artifacts when encountered; never commit `.env`, `instance/*.db`,
     `node_modules`, model weights, or files >50 MB (GitHub rejects >100 MB;
     ignore patterns must use `**` to match subdirectories — a 102 MB zip
     once slipped past `notebooks/*.zip`).

---

## 8. Key reference documents

| Doc | Why open it |
|---|---|
| `PHASE1_STATUS.md` | Why metrics were reset to null; honesty rules |
| `PHASE2_STATUS.md` | Exact Kaggle training + eval runbook |
| `docs/ARCHITECTURE.md` | Mermaid diagrams, service inventory |
| `README.md` | Public narrative (slightly stale re: frontend paths) |
| `n8n-workflows/N8N_SUBSCRIPTION_GUIDE.md` | Alert-email setup (endpoints listed there are stale — see Phase D item 3) |
