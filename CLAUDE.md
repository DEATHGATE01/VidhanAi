# Hermes Agent — Project Instructions

This file is the standing instruction set for any AI assistant (Claude, etc.) or
human contributor working on **Hermes Agent**. Read this fully before doing
anything else in the repo. Keep it up to date as the project evolves.

---

## 1. Project Snapshot

- **Project name:** VidhanAI
- **One-line purpose:** Generative AI legislative simplification engine for Indian
  parliamentary bills (data source: PRS India BillTrack).
- **Tech stack:** Python/Flask + SQLAlchemy + SQLite backend · ChromaDB semantic
  RAG · React 19 + Vite + Tailwind CSS 4 frontend · Groq API / locally fine-tuned
  Llama-3.2-3B (Ollama) for LLM generation · n8n workflows for alert emails.
- **Repo URL:** https://github.com/DEATHGATE01/VidhanAi
- **Primary branch:** `main`
- **Owner / maintainer:** DEATHGATE01 (academic/internship project)

---

## 2. How to Start a Session (read this every time)

1. Read this `CLAUDE.md` fully.
2. Read `TASKS.md` — check for tasks marked `IN_PROGRESS`. If another session
   is actively working on something, **do not touch the same files** — pick a
   different task or coordinate first (see §5).
3. Read the last 5–10 entries of `SESSION_LOG.md` to understand recent history
   and any open decisions.
4. Run `git status` and `git log --oneline -10` to confirm the working tree
   matches what the logs say.
5. Only then start work — and log your start (see §5.2).

---

## 3. Professionalism & Communication Standards

- Write commit messages, code comments, and docs as if a new teammate will
  read them cold — no inside jokes, no ambiguous shorthand.
- Prefer clarity over cleverness. Explain *why*, not just *what*, in comments
  for non-obvious logic.
- Never leave `TODO`/`FIXME` without a short note on what's missing and why
  it was deferred.
- Flag assumptions explicitly (e.g. `// ASSUMPTION: input is always UTF-8`)
  rather than silently guessing.
- No destructive actions (force-push to `main`, dropping data, deleting
  branches others may need) without explicit confirmation from the user.
- If something is ambiguous or risky, say so plainly and propose options
  rather than silently picking one and hoping it's right.

---

## 4. Git & GitHub Best Practices

**Branching**
- `main` is always deployable. Never commit directly to `main`.
- Branch naming: `feature/<short-desc>`, `fix/<short-desc>`,
  `chore/<short-desc>`, `docs/<short-desc>`.
- One branch per task/feature — keep branches short-lived.

**Commits**
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
  `chore:`.
- Small, atomic commits. One logical change per commit.
- Never commit secrets, API keys, `.env` files, or credentials. Add them to
  `.gitignore` immediately if they appear.
- Never commit model weights, fabricated results, or files >50 MB (GitHub
  rejects >100 MB). Metrics only from
  `backend/scripts/ml_pipeline/3_calculate_metrics.py` with a real adapter,
  or explicitly labeled Groq fallback — never fabricated.

**Pull Requests**
- Every change to `main` goes through a PR, even for solo work — it creates a
  reviewable trail.
- PR description: what changed, why, how it was tested, and any follow-up
  needed.
- Keep PRs small enough to review in one sitting.
- Link related issues/tasks (see `TASKS.md`) in the PR description.

**General hygiene**
- `.gitignore` covers build artifacts, dependency folders, env files, IDE
  configs, and OS junk files.
- Tag releases with semantic versioning (`v0.1.0`, `v1.0.0`, ...).
- Write a `README.md` that lets a stranger clone, install, and run the
  project in under 5 minutes.
- Run tests/linters before committing; don't commit code that fails CI.
- Commit at every phase boundary (resume-grade history): one conventional
  commit per completed phase, staged by subsystem (`git add <paths>`, never
  blind `git add -A`), pushed to origin immediately after.

---

## 5. Cross-Session Coordination (multiple sessions, same project)

The core problem: several sessions (or people) may work on this project at
different times without talking to each other directly. `TASKS.md` and
`SESSION_LOG.md` are the shared memory that prevents collisions.

### 5.1 `TASKS.md` — the task ledger
- Every task has: **ID, title, status, owner/session-tag, files touched,
  last updated**.
- Status values: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`.
- **Before starting a task:** mark it `IN_PROGRESS` and note which files/areas
  you'll touch, *before* you start editing.
- **Before touching any file:** scan `TASKS.md` for other `IN_PROGRESS` tasks
  that list the same file. If found, don't edit it — pick something else or
  leave a note.
- **On finishing:** mark `DONE`, or `BLOCKED` with a reason if you couldn't
  finish, and summarize what's left.
- Never delete old tasks — move completed ones to a "Done" section so history
  is preserved.

### 5.2 `SESSION_LOG.md` — the running diary
- At the **start** of a session: append an entry with timestamp, what you
  intend to work on.
- At the **end** of a session (or when handing off): append what you did,
  what changed, what's unresolved, and what the next session should know.
- This is prose, not just a task status — it's where "gotchas", partial
  reasoning, and context live that don't fit in a task ledger.

### 5.3 Conflict avoidance rules
- If you find a task already `IN_PROGRESS` from a recent session (check the
  timestamp — "recent" means within a reasonable working window), assume it
  might still be active. Don't silently take it over or redo it.
- If a task looks stale (`IN_PROGRESS` for a long time with no log entries),
  flag it in `SESSION_LOG.md` rather than assuming it's abandoned and barging
  in.
- Prefer working on separate files/modules per task to minimize merge
  conflicts between sessions.
- Always `git pull`/sync before starting, and commit+push before ending, so
  the next session sees current state.

---

## 6. Tool Permissions (Claude Code / agent tool access)

Repeated permission prompts happen because, by default, coding agents ask
before running shell commands, editing files, etc. You can reduce prompts
**safely** without giving blanket unrestricted access:

- Prefer an **allowlist** of specific safe operations over a full bypass.
  In Claude Code this is configured in `.claude/settings.json`, e.g.:
  ```json
  {
    "permissions": {
      "allow": [
        "Bash(git *)",
        "Bash(npm *)",
        "Edit",
        "Read"
      ]
    }
  }
  ```
  Adjust the list to the commands this project actually needs.
- There is also a "skip all permission checks" mode
  (`--dangerously-skip-permissions` in Claude Code), but it does exactly what
  the name says: it removes the safety net for *every* action, including
  destructive ones. If you use it, do so only in a disposable/sandboxed
  environment, not on a machine with things you can't afford to lose — a
  blanket bypass is a tradeoff, not a free win.
- A middle ground that covers most day-to-day friction: allow read/edit/git
  operations broadly, but keep destructive commands (`rm -rf`, force-push,
  `git reset --hard`, database drops, etc.) behind confirmation.
- Re-review the allowlist occasionally as the project grows instead of
  widening it reflexively whenever something prompts.

---

## 7. Coding Standards

- **Linting/formatting:** frontend — `npm run lint` (oxlint, already
  configured in `frontend_new`); backend — Ruff if installed (`uv` is
  available on this machine). No enforced formatter; keep diffs clean and
  don't reformat untouched code.
- **Testing:** no test suite yet. Verify frontend changes with
  `npm run build` (must pass) and backend changes with `python -m py_compile`
  plus a live smoke test against `http://127.0.0.1:5000/api/health`.
- **Directory structure:** `backend/` (Flask app + scripts),
  `frontend_new/` (the single frontend — there is no `frontend/` dir),
  `notebooks/` (Kaggle training), `n8n-workflows/`, `docs/`.
- **Error handling / logging:** backend responses use the `{success, ...}` /
  `{error}` envelope; LLM features must degrade gracefully (extractive
  fallback) when keys/services are unavailable, never crash the app.
- **How to run:** backend `cd backend && python app.py` (port 5000; needs
  `backend/.env` with `GROQ_API_KEY` for LLM features); frontend
  `cd frontend_new && npm run dev` (port 5173). `backend/config.py` is
  intentionally empty — configuration lives in `app.py` + environment
  variables; don't "fix" that without a reason.

---

## 8. File Map for This Instruction Set

- `CLAUDE.md` — this file. Standing rules, read every session.
- `TASKS.md` — live task ledger (status, owner, files touched).
- `SESSION_LOG.md` — chronological diary of what happened each session.

Keep all three in the repo root so every session (and every contributor)
finds them immediately.