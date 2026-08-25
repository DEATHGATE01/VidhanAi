# VidhanAI — Phase 1 Status (Reproducibility & Honest Framing)

> Semester continuation, Phase 1 of the multi-phase plan.
> Scope picked by the team: **foundation (reproducibility) only**.
> Canonical headline metrics (paper's): **ROUGE-1 = 0.47 (+51.6%), BLEU = 8.73 (+107.4%)**.

## Why Phase 1 exists

The research paper (`RESEARCH PAPER(VIDHAN AI).docx`) and IEEE report
(`docs/IEEE_Report.md`) make several claims that the previous version of the
code did not actually defend:

1. The "fine-tuned" column in `metrics_summary.json` was produced by a **Groq
   `llama-3.3-70b-versatile` API call with the expert prompt**, not by the
   QLoRA-fine-tuned Llama-3.2-3B the paper claims to evaluate.
2. The test set was **n = 2 samples** — far too small to support the
   percentage deltas in Tables III and VII of the paper.
3. `ai_service.py` silently fell back to an extractive summarizer whenever the
   (non-existent) LoRA adapter was missing, while reporting the summary as the
   fine-tuned model.
4. The dataset generator scraped PRS India **live** every run, so the dataset
   was not reproducible.

Phase 1 fixes (1)–(4) without yet producing real QLoRA numbers — that is
Phase 2 on Kaggle.

## What Phase 1 changed

### `backend/ai_service.py` — honest model handling
- Three clearly-named backends: `groq_expert` (default, production),
  `local_lora` (Phase 2, opt-in via `VIDHANAI_USE_LORA=1`), and
  `rule_based_extractive_v1` (last-resort).
- Every summary now records `model_version`, `guardrail_applied`, and
  `guardrail_version` so reviewers can audit which backend produced it.
- Local LoRA path is gated behind `VIDHANAI_USE_LORA` so we never silently
  fall back from a real adapter run to Groq.

### `backend/models.py` and `backend/db_service.py` — schema for auditability
- `BillSummary` now has `model_version`, `guardrail_applied`,
  `guardrail_version` columns so the database records which backend produced
  each summary and whether the disclaimer was appended.
- `BillSummary.to_dict()` surfaces those fields in the API response.
- Table count verified: **11 SQLite tables** are defined by `models.py`, which
  matches the paper's §III.B claim. The legacy duplicate
  `backend/subscription_models.py` is dead code (not imported anywhere); it
  was not deleted during Phase 1 to avoid breaking auto-registered models, but
  should be removed once verified.

### `backend/scripts/ml_pipeline/1_generate_dataset.py` — reproducible dataset
- Reads source bill text from the local SQLite database (not live scraping),
  so the run is deterministic given the same DB.
- Targets **≥100 samples** (default 120) with an 80/10/10 split
  (`train.jsonl` / `val.jsonl` / `test.jsonl`).
- Resumable: each Groq-generated row is appended to
  `datasets/generation_log.jsonl` as it lands, so an interrupted run picks up
  where it left off.
- Per-row schema validation (`instruction`, `input`, `output`).
- CLI flags: `--num-samples`, `--output-dir`, `--db-path`, `--model`,
  `--seed`, `--no-resume`, `--min-text-chars`, `--max-text-chars`.

### `backend/scripts/ml_pipeline/3_calculate_metrics.py` — honesty-first eval
- Detects whether a real LoRA adapter exists at `notebooks/lora_model`.
  - If yes → runs a proper **zero-shot Llama-3.2-3B baseline vs LoRA-fine-tuned**
    evaluation locally.
  - If no → exits cleanly with a "Phase 2 required" message and **does NOT**
    overwrite `metrics_summary.json` with fake numbers.
- Adds **bootstrap 95% confidence intervals** (1000 resamples) to every ROUGE
  and BLEU metric, plus a raw `docs/metrics_bootstrap.json` for plotting.
- Old "compare two Groq API calls" behaviour is gated behind
  `--allow-groq-fallback` (off by default) so it can never run by accident
  and be mistaken for a QLoRA result.

### `docs/metrics_summary.json` — placeholder until Phase 2
- Set to `status: "pending_phase_2_lora_training"` with the planned evaluation
  config (zero-shot vs QLoRA on the expanded test set).
- All metric fields are `null` until a real adapter exists.

### `docs/IEEE_Report.md` — honest framing
- Added a "Status Update — Phase 1" callout under the abstract.
- Added a "Phase 1 note" box above the §IV results table stating that the
  numbers there are the *target* numbers Phase 2 will reproduce, and that the
  current 70B column was a prompt-engineering stand-in.
- Added a note next to the hallucination figure clarifying it came from a
  manual audit against the 70B stand-in, and that the Phase 2 audit will use
  two annotators with inter-annotator agreement.

### `docs/failure_cases.md` — honest framing
- Header now states the production summarizer is Groq 70B with the expert
  prompt, and the 12 documented failure cases are illustrative of expected
  failure modes; the log will be regenerated against the real LoRA model in
  Phase 2.

## Phase 1 verification commands

```bash
# 1. Regenerate the dataset (≥100 samples). Requires GROQ_API_KEY in backend/.env.
cd backend/scripts/ml_pipeline
python 1_generate_dataset.py --num-samples 120

# 2. Run the honest evaluation. Without an adapter this exits cleanly:
python 3_calculate_metrics.py
# Expected: "[No trained LoRA adapter at notebooks/lora_model ...]"

# 3. (Optional) Sanity-check Groq-only numbers, explicitly opting in:
python 3_calculate_metrics.py --allow-groq-fallback --max-samples 20
```

## What is deliberately deferred

### Phase 2 — QLoRA training on Kaggle T4×2 (next session)
- Train the real adapter: `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`, 4-bit NF4,
  r=16, α=16, lr=2e-4, AdamW 8-bit, gradient checkpointing, ~60 epochs on the
  ≥100-sample training split.
- Save adapter to `notebooks/lora_model/`, set `VIDHANAI_USE_LORA=1`, and run
  `3_calculate_metrics.py` to produce the real headline numbers with
  bootstrap CIs.
- Manually audit 20 LoRA summaries vs 20 zero-shot summaries for the
  hallucination table (two annotators, inter-annotator agreement).

### Phase 3 — Pipeline completeness (the 11-phase pipeline)
- Phase 2 (PDF extraction): currently only HTML list pages are scraped; add
  PDF download + text extraction to reach the paper's "97 bills / 7.2M chars"
  figure and beyond.
- Phase 3 (structure parsing): persist parsed sections/clauses into
  `BillContent.sections` so the paper's "avg 150 sections / 70 clauses per
  bill" stat is reproducible.
- Phase 4 (version tracking): wire `BillVersion` into a real change-log
  generator (currently `track_bill_version` exists but nothing calls it).
- Phase 7 (news collection): add the Google News RSS fetcher producing the
  paper's 485 linked articles.
- Phase 8 (multi-task sentiment): sentiment + stance + sarcasm classifier,
  not just TextBlob polarity.
- Phase 9 (temporal analysis): bill timelines from real event data, not
  the status-string heuristic in `routes.py`.
- Verify ChromaDB embedding count reaches the paper's 12,018 vectors.

### Phase 4 — Guardrails & hallucination eval harness
- 45-sample guardrail test set across 5 categories
  (legal / creative / prompt-injection / code / ambiguous).
- Hallucination audit harness that auto-checks generated penalty amounts and
  dates against the source text.

### Phase 5 — Dashboard & stakeholder features
- Sentiment chart on the bill detail page (currently only ministry pie).
- Real timeline view tied to `BillVersion` rows.
- Newsletter generation + amendment alerts (currently `UserSubscription`
  schema exists but no sender).

### Phase 6 — Delta-aware summarization (proposal's new research contribution)
- Amendment alignment across versions, change-specific summaries, distinct
  evaluation metrics, alert-when-changed notification hook.

## Open decisions for Phase 2
- Confirm LoRA base model: `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` (matches
  paper) — verify it still downloads cleanly on Kaggle.
- Confirm target test-set size: paper said 2; proposal says several hundred.
  Recommend **≥50 test, ≥100 train** as a defensible floor.
- Decide whether to keep the existing 19-sample `train.jsonl`/`val.jsonl`/
  `test.jsonl` or regenerate from scratch with `--no-resume`.

## Reference map
- Paper claims: `RESEARCH PAPER(VIDHAN AI).docx` (root)
- Proposal (next-phase plan): `VidhanAI_Proposal.docx` (root)
- IEEE report (paper draft being defended): `docs/IEEE_Report.md`
- Old metrics framing (rejected): superseded by this phase.
