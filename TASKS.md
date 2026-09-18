# TASKS.md — Task Ledger

Cross-session task ledger for this repo. See `CLAUDE.md` §5 for the rules:
mark a task `IN_PROGRESS` with the files you'll touch *before* editing; scan
for colliding `IN_PROGRESS` tasks first; on finish mark `DONE` or `BLOCKED`
with a reason. Never delete old tasks — move them to the Done section.

Last updated: 2026-09-18

---

## Active

_No tasks are currently `IN_PROGRESS`._

---

## TODO

| ID | Title | Status | Owner/Session | Files touched | Last updated |
|----|-------|--------|---------------|---------------|--------------|
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
