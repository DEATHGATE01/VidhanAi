# VidhanAI — Phase 2 Status (Real QLoRA Fine-Tuning)

> Phase 2 of the multi-phase plan (see `PHASE1_STATUS.md`).
> Goal: train the *real* Llama-3.2-3B QLoRA adapter the paper claims, evaluate
> it honestly against a zero-shot baseline with bootstrap CIs, and regenerate
> the hallucination audit.

## What Phase 2 builds

### 1. `backend/app.py` — Flask entry point (NEW, was missing)
- **The backend had no `app.py`** even though `start.bat`, the READMEs, and
  `fetch_all_bill_data.py` all call `python app.py` / `from app import create_app`.
- Added a `create_app()` factory (matches the contract existing scripts already
  expected): SQLAlchemy init, `api` blueprint under `/api`, CORS for the Vite
  dev servers, auto-creates the 11-table schema on first run.
- Verified: `GET /api/health` → 200 and `GET /` → 200.
- `backend/subscription_models.py` (duplicate table definitions) is now a
  deprecated shim re-exporting from `models.py`.

### 2. `backend/scripts/setup/seed_bills_for_ft.py` (NEW)
- Populates the SQLite DB with bill metadata + full text from PRS so the
  dataset generator has ≥100 distinct bills with content.
- Idempotent/resumable: skips bills that already have content; `--refresh` to
  re-fetch; `--stats` to report DB readiness.
- Verified: imports + `--stats` path run cleanly.

### 3. `notebooks/qlora_finetuning.ipynb` (REBUILT for the paper's model)
- The old notebook trained **Llama-3-8B**, which does **not** match the paper's
  Table II (**Llama-3.2-3B**) or `ai_service.py` (`unsloth/Llama-3.2-3B-Instruct-bnb-4bit`).
- Rebuilt for **Kaggle T4 x2**: 4-bit NF4, r=16, α=16, q/k/v/o/gate/up/down,
  lr=2e-4, AdamW-8bit, batch 2, grad-accum 4 (effective 8), max_steps 60,
  max_seq_len 2048 — exactly the paper's hyperparameters.
- Cell-by-cell: install deps → load base in 4-bit → attach LoRA → load
  train/val JSONL (via Kaggle dataset input) → SFTTrainer → export to
  `lora_model/` → quick inference sanity check.
- Validated as nbformat 4 (11 cells).

### 4. `notebooks/roundtrip_lora.py` (NEW)
- `--bundle-dataset`: zips `datasets/{train,val,test}.jsonl` +
  `dataset-metadata.json` for drag-and-drop into a new Kaggle Dataset.
- `--extract-adapter <zip>`: unzips a downloaded `lora_model/` into
  `notebooks/lora_model/`, **refusing to install stubs** (weights < 1 MB are
  rejected — verified the 133-byte placeholder is correctly refused).
- Verified: bundler works; stub-rejection works.

### 5. Stub quarantine (CRITICAL honesty fix)
- `notebooks/lora_model/` shipped a **133-byte `adapter_model.safetensors`**
  placeholder — a fake "trained" artifact. Anything that queried that directory
  (`lora_adapter_available()`, `lora_adapter_present()`) would report a trained
  model existed when none did.
- Both `backend/ai_service.py` and `backend/scripts/ml_pipeline/3_calculate_metrics.py`
  now require real weights (≥ 1 MB) before treating an adapter as present.
- Effect: until the Kaggle-trained adapter is installed, the eval script exits
  cleanly with a "Phase 2 required" message and writes **no** fake metrics, and
  `ai_service.py` will never load the stub even with `VIDHANAI_USE_LORA=1`.

### 6. `backend/requirements.txt` (updated)
- ML training deps (transformers/peft/accelerate/bitsandbytes) moved behind a
  comment block with a note that training runs on Kaggle; they're only needed
  locally for running `3_calculate_metrics.py` against a real adapter.

### 7. Groq model change (IMPORTANT)
- The paper and older scripts reference `llama-3.3-70b-versatile` and
  `llama-3.1-8b-instant`. **Groq has retired both.** The current flagship text
  model on the project key is **`groq/compound`** (and `gpt-oss-120b`, which
  was observed returning empty bodies on this key). Everything now defaults to
  `groq/compound`, overridable via `VIDHANAI_GROQ_MODEL`.
- This affects the paper's "Teacher model" description. Update the paper to say
  the golden summaries were generated with `groq/compound` (Groq's current
  flagship), noting the original model was retired — or regenerate the whole
  dataset truthfully, which is what the current seed/dataset pipeline does.

### 8. Rate-limit handling
- Groq free tier is ~30 requests/min. `1_generate_dataset.py` now uses
  `Groq(max_retries=8)` plus a 3.5s inter-call sleep so transient 429s are
  absorbed as small waits instead of dropping bill samples. The first attempt
  dropped ~90% of rows at 2s pacing + default retries; after tuning it keeps
  nearly all rows. Resume is safe via `generation_log.jsonl`.

## Run this in order

```bash
# 0) One-time: create a Groq key, put it in backend/.env as GROQ_API_KEY

# 1) Seed the DB with ≥100 bills that have full text (takes a while vs PRS):
cd backend
python scripts/setup/seed_bills_for_ft.py --limit 180 --delay 1.0
python scripts/setup/seed_bills_for_ft.py --stats   # expect usable_bills_for_ft >= 100

# 2) Generate the fine-tuning dataset (deterministic, resumable):
cd backend/scripts/ml_pipeline
python 1_generate_dataset.py --num-samples 120
# Produces datasets/train.jsonl (96), val.jsonl (12), test.jsonl (12) + generation_log.jsonl

# 3) Bundle for Kaggle:
cd ../../../
python notebooks/roundtrip_lora.py --bundle-dataset
# -> notebooks/vidhanai_ft_dataset.zip

# 4) On Kaggle (kaggle.com):
#    - Datasets -> Existing datasets? No -> New Dataset -> upload the zip. Note the slug.
#    - Create a Kaggle Notebook (GPU T4 x2), Add Input -> your dataset.
#    - Edit the TRAIN_PATH/VAL_PATH constant in cell 2.
#    - Run all cells. Download notebooks/qlora_finetuning.ipynb's lora_model/ dir.

# 5) Install the real adapter locally:
python notebooks/roundtrip_lora.py --extract-adapter path/to/lora_model.zip

# 6) Honest evaluation (bootstrap CIs, no fake numbers):
cd backend/scripts/ml_pipeline
python 3_calculate_metrics.py
# Writes docs/evaluation_results.csv, docs/metrics_summary.json, docs/metrics_bootstrap.json
```

## Expected runtime on Kaggle

- 60 steps, Llama-3.2-3B, batch 2 ×4 accum: **~5–10 minutes** on one T4.
- T4 x2 is comfortable; the notebook uses a single device but the extra GPU is
  headroom against OOM.

## Deferred to Phase 3+ (unchanged from PHASE1_STATUS.md)

- PDF extraction beyond the HTML pages PRS exposes (paper claims 97 bills /
  7.2M chars).
- Structural section/clause statistics at scale.
- News collection (485 articles), multi-task sentiment (stance/sarcasm),
  timeline generation.
- Guardrail 45-sample test harness + two-annotator hallucination audit with
  inter-annotator agreement.
- Dashboard sentiment/timeline views and amendment alerts.
- Delta-aware summarization (proposal's new research contribution).

## Open decisions for the team

1. **Dataset size:** `--num-samples 120` gives 96/12/12 — defensible. If PRS is
   flaky, aim for ≥80 total and proceed; the eval script doesn't hard-depend on
   split counts.
2. **GPU:** paper says "Colab T4"; we're using **Kaggle T4 x2** (user decision)
   for 30h/week free quota. Update the paper's Platform row in Table II to
   "Google Colab T4 / Kaggle T4 x2".
3. **Adapter storage:** keep `lora_model/` gitignored? If yes, add `/notebooks/lora_model/adapter_model.safetensors` to `.gitignore` so the stub doesn't come back.