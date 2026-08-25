"""
Phase 1 evaluation pipeline - honesty-first design.

This script used to compare two Groq API calls (a generic 8B baseline against
an expert-prompt 70B "fine-tuned") and write those numbers to
``docs/metrics_summary.json``. That framing was misleading: the headline
percentages in the IEEE paper were presented as a QLoRA-vs-zero-shot comparison,
but the numbers were actually a small-vs-large-model prompt-engineering
comparison.

Phase 1 of the semester plan fixes that. The script now does ONE thing:

    * Detect whether a real QLoRA adapter is present at the configured path.
    * If yes: run a proper baseline-vs-fine-tuned evaluation using the actual
      Llama-3.2-3B base model and the LoRA adapter.
    * If no: exit with a clear "Phase 2 required" message and DO NOT touch
      ``metrics_summary.json``.

Bootstrap confidence intervals are computed on every metric so future runs
report statistical spread, not a single sample mean.

Outputs (when run with an adapter present):
    * docs/evaluation_results.csv  - per-sample side-by-side comparisons
    * docs/metrics_summary.json    - aggregate metrics with bootstrap CIs
    * docs/metrics_bootstrap.json  - raw bootstrap distribution for plotting
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:  # pragma: no cover
    PANDAS_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:  # pragma: no cover
    TQDM_AVAILABLE = False

try:
    import evaluate
    EVALUATE_AVAILABLE = True
except ImportError:  # pragma: no cover
    EVALUATE_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:  # pragma: no cover
    GROQ_AVAILABLE = False

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    LORA_AVAILABLE = True
except ImportError:  # pragma: no cover
    LORA_AVAILABLE = False


# ---------------------------------------------------------------------------
# Paths & configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent

DATASET_PATH = SCRIPT_DIR / "datasets" / "test.jsonl"
DOCS_DIR = PROJECT_ROOT / "docs"
RESULTS_CSV = DOCS_DIR / "evaluation_results.csv"
METRICS_JSON = DOCS_DIR / "metrics_summary.json"
BOOTSTRAP_JSON = DOCS_DIR / "metrics_bootstrap.json"

# Defaults match the paper's QLoRA setup.
LORA_BASE_MODEL = os.environ.get("VIDHANAI_LORA_BASE", "unsloth/Llama-3.2-3B-Instruct-bnb-4bit")
LORA_ADAPTER_DIR = os.environ.get(
    "VIDHANAI_LORA_DIR",
    str(PROJECT_ROOT / "notebooks" / "lora_model"),
)
LORA_ADAPTER_DIR_PATH = Path(LORA_ADAPTER_DIR)

EXPERT_SYSTEM_PROMPT = (
    "You are an expert legal translator. Summarize this Indian legislative "
    "text into plain, accessible English suitable for a high school reading "
    "level. Retain all factual penalties, dates, and jurisdictions. Format "
    "the output clearly with headings and bullet points. Do not include "
    "meta-commentary about your approach, notes to the reader, or headings "
    "such as 'Here is the summary' / 'How I approached this'."
)
# The paper referenced `llama-3.3-70b-versatile`, which Groq has since retired.
# `groq/compound` is the current flagship text model on the project's key.
GROQ_FALLBACK_TEACHER = os.environ.get("VIDHANAI_GROQ_MODEL", "groq/compound")
INSTRUCTION = "Simplify this legal text"

BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 42


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("vidhanai.evaluate")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# ---------------------------------------------------------------------------
# Adapter detection
# ---------------------------------------------------------------------------

MIN_REAL_SAFETENSORS_BYTES = 1_000_000  # a stub placeholder is ~133 bytes
BITSANDBYTES_AVAILABLE = False
try:
    import bitsandbytes as bnb  # noqa: F401
    BITSANDBYTES_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass


def lora_adapter_present(path: Path) -> bool:
    """Return True iff ``path`` holds a *real* trained PEFT adapter.

    Rejects stubs: the repo ships a 133-byte `adapter_model.safetensors`
    placeholder from before Phase 2. A trained LoRA adapter for a 3B model
    has weights tens of MB in size, so anything below the threshold is
    treated as absent to avoid evaluating (or presenting) a fake adapter.
    """
    if not path.is_dir():
        return False
    weights = [
        fname for fname in os.listdir(path)
        if fname.endswith((".safetensors", ".bin", ".pt"))
    ]
    has_weights = any(
        os.path.getsize(path / fname) >= MIN_REAL_SAFETENSORS_BYTES
        for fname in weights
    )
    has_config = (path / "adapter_config.json").exists()
    return has_weights and has_config


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_test_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if {"instruction", "input", "output"}.issubset(row):
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Local LoRA inference
# ---------------------------------------------------------------------------

def generate_local_predictions(rows: list[dict], base_model_name: str, adapter_dir: Path,
                               backend: str) -> list[str]:
    """backend is either 'baseline' (raw base model) or 'finetuned' (LoRA adapter)."""
    if not LORA_AVAILABLE:
        raise RuntimeError(
            "transformers/peft not installed; cannot run local evaluation."
        )
    if not torch.cuda.is_available():
        logger.warning("No CUDA detected; running on CPU. This will be slow.")

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    # On CPU: use fp16 to halve RAM (~6 GB vs ~12 GB for a 3B model).
    # The eval is for relative comparison, not numerical fidelity.
    if torch.cuda.is_available():
        dtype = torch.float16
    else:
        dtype = torch.float16  # fp16 is fine on CPU and uses half the memory
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        device_map="auto",
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    if backend == "finetuned":
        model = PeftModel.from_pretrained(model, str(adapter_dir))
        model.eval()

    predictions: list[str] = []
    iterator = tqdm(rows, desc=f"local-{backend}") if TQDM_AVAILABLE else rows
    for row in iterator:
        text = row["input"][:6000]
        messages = [
            {"role": "system", "content": EXPERT_SYSTEM_PROMPT},
            {"role": "user", "content": f"{INSTRUCTION}:\n\n{text}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        input_length = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_length:]
        predictions.append(tokenizer.decode(new_tokens, skip_special_tokens=True).strip())

    # Free GPU memory before any subsequent runs.
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return predictions


# ---------------------------------------------------------------------------
# Groq fallback (only used if --allow-groq-fallback is set; off by default)
# ---------------------------------------------------------------------------

def generate_groq_predictions(rows: list[dict], model: str, system_prompt: str) -> list[str]:
    if not GROQ_AVAILABLE:
        raise RuntimeError("groq package not installed.")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set.")
    client = Groq(api_key=api_key)
    predictions: list[str] = []
    iterator = tqdm(rows, desc=f"groq-{model}") if TQDM_AVAILABLE else rows
    for row in iterator:
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Simplify this legal text:\n\n{row['input'][:8000]}"},
                ],
                model=model,
                temperature=0.3,
                max_tokens=1024,
            )
            predictions.append((response.choices[0].message.content or "").strip())
        except Exception as exc:  # pragma: no cover
            logger.warning("Groq call failed: %s", exc)
            predictions.append("")
        time.sleep(1)
    return predictions


# ---------------------------------------------------------------------------
# Metrics + bootstrap
# ---------------------------------------------------------------------------

def compute_metrics(predictions: list[str], references: list[str]) -> dict:
    rouge = evaluate.load("rouge")
    bleu = evaluate.load("sacrebleu")
    rouge_scores = rouge.compute(predictions=predictions, references=references)
    bleu_score = bleu.compute(predictions=predictions, references=[[r] for r in references])["score"]
    return {
        "rouge1": round(float(rouge_scores["rouge1"]), 4),
        "rouge2": round(float(rouge_scores["rouge2"]), 4),
        "rougeL": round(float(rouge_scores["rougeL"]), 4),
        "bleu": round(float(bleu_score), 4),
    }


def bootstrap_ci(metric_fn, predictions: list[str], references: list[str],
                 n_resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED) -> dict:
    """Return point estimate + 95% CI for each metric, plus the raw resample dist."""
    import random as rnd

    if len(predictions) != len(references) or len(predictions) < 2:
        return {"samples": [], "ci_low": None, "ci_high": None, "mean": None}

    rnd.seed(seed)
    n = len(predictions)
    sampled_metrics: list[dict] = []
    for _ in range(n_resamples):
        idx = [rnd.randrange(n) for _ in range(n)]
        sample_preds = [predictions[i] for i in idx]
        sample_refs = [references[i] for i in idx]
        sampled_metrics.append(metric_fn(sample_preds, sample_refs))

    metric_names = sampled_metrics[0].keys()
    summary = {}
    for name in metric_names:
        values = [m[name] for m in sampled_metrics]
        values_sorted = sorted(values)
        ci_low = values_sorted[int(0.025 * n_resamples)]
        ci_high = values_sorted[int(0.975 * n_resamples) - 1]
        summary[name] = {
            "mean": round(statistics.mean(values), 4),
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            "median": round(statistics.median(values), 4),
        }
    summary["_resamples"] = [
        {k: round(v, 4) for k, v in m.items()} for m in sampled_metrics[:200]
    ]
    summary["_n_resamples"] = n_resamples
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--adapter-dir", type=Path, default=LORA_ADAPTER_DIR_PATH)
    parser.add_argument("--base-model", type=str, default=LORA_BASE_MODEL,
                        help="HF repo id of the base model. For CPU eval of a "
                             "4-bit-trained adapter, pass the non-quantized "
                             "checkpoint (e.g. unsloth/Llama-3.2-3B-Instruct).")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Cap number of test rows (useful for quick sanity checks).")
    parser.add_argument("--allow-groq-fallback", action="store_true",
                        help="Allow evaluating against Groq if no LoRA adapter is found. "
                             "Off by default because the paper claims a QLoRA run.")
    parser.add_argument("--groq-model", type=str, default="groq/compound")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if load_dotenv is not None:
        env_path = BACKEND_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    if not EVALUATE_AVAILABLE:
        logger.error("`evaluate` package missing. pip install evaluate rouge_score sacrebleu")
        return 1
    if not PANDAS_AVAILABLE:
        logger.error("pandas missing. pip install pandas")
        return 1

    rows = load_test_rows(args.dataset)
    if not rows:
        logger.error("Test dataset empty or missing at %s", args.dataset)
        logger.error("Run 1_generate_dataset.py first.")
        return 1
    if args.max_samples:
        rows = rows[: args.max_samples]
    logger.info("Loaded %d test samples.", len(rows))

    references = [row["output"] for row in rows]
    inputs = [row["input"] for row in rows]

    if lora_adapter_present(args.adapter_dir):
        logger.info("Found LoRA adapter at %s. Running local QLoRA evaluation.",
                    args.adapter_dir)
        baseline_preds = generate_local_predictions(rows, args.base_model,
                                                    args.adapter_dir, backend="baseline")
        finetuned_preds = generate_local_predictions(rows, args.base_model,
                                                     args.adapter_dir, backend="finetuned")
        baseline_model_version = args.base_model
        finetuned_model_version = f"lora-on-{args.base_model}"
    else:
        if not args.allow_groq_fallback:
            logger.warning("=" * 70)
            logger.warning("No trained LoRA adapter at %s.", args.adapter_dir)
            logger.warning("The IEEE paper's headline numbers come from a real QLoRA")
            logger.warning("fine-tune of Llama-3.2-3B. Until that exists (Phase 2,")
            logger.warning("Kaggle), this script will NOT generate metrics.")
            logger.warning("Pass --allow-groq-fallback to compare Groq models instead.")
            logger.warning("=" * 70)
            return 2

        logger.warning("Using Groq fallback evaluation (NOT a QLoRA run).")
        baseline_preds = generate_groq_predictions(
            rows, args.groq_model, system_prompt="Summarize the following text."
        )
        finetuned_preds = generate_groq_predictions(
            rows, GROQ_FALLBACK_TEACHER, system_prompt=EXPERT_SYSTEM_PROMPT,
        )
        baseline_model_version = f"groq:{args.groq_model}"
        finetuned_model_version = f"groq:{GROQ_FALLBACK_TEACHER}"

    logger.info("Computing ROUGE/BLEU...")
    baseline_metrics = compute_metrics(baseline_preds, references)
    finetuned_metrics = compute_metrics(finetuned_preds, references)

    delta = {k: round(finetuned_metrics[k] - baseline_metrics[k], 4)
             for k in baseline_metrics}

    logger.info("Baseline: %s", baseline_metrics)
    logger.info("Fine-Tuned: %s", finetuned_metrics)
    logger.info("Delta: %s", delta)

    logger.info("Computing bootstrap CIs over %d resamples...", BOOTSTRAP_RESAMPLES)
    baseline_ci = bootstrap_ci(compute_metrics, baseline_preds, references)
    finetuned_ci = bootstrap_ci(compute_metrics, finetuned_preds, references)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if PANDAS_AVAILABLE:
        df = pd.DataFrame({
            "bill_id": [row.get("bill_id", "?") for row in rows],
            "Document Snippet": [inp[:150] + "..." for inp in inputs],
            "Golden Summary": references,
            "Baseline Output": baseline_preds,
            "Fine-Tuned Output": finetuned_preds,
        })
        df.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
        logger.info("Wrote %s", RESULTS_CSV)

    summary = {
        "evaluation_config": {
            "test_samples": len(rows),
            "baseline_model": baseline_model_version,
            "finetuned_model": finetuned_model_version,
            "golden_reference": f"expert prompt via Groq {GROQ_FALLBACK_TEACHER}",
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "baseline_metrics": baseline_metrics,
        "finetuned_metrics": finetuned_metrics,
        "improvement_delta": delta,
        "bootstrap": {
            "baseline": {k: v for k, v in baseline_ci.items() if not k.startswith("_")},
            "finetuned": {k: v for k, v in finetuned_ci.items() if not k.startswith("_")},
        },
    }
    with METRICS_JSON.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    logger.info("Wrote %s", METRICS_JSON)

    bootstrap_dump = {
        "baseline_resamples": baseline_ci.get("_resamples", []),
        "finetuned_resamples": finetuned_ci.get("_resamples", []),
        "n_resamples": BOOTSTRAP_RESAMPLES,
    }
    with BOOTSTRAP_JSON.open("w", encoding="utf-8") as handle:
        json.dump(bootstrap_dump, handle, indent=2)
    logger.info("Wrote %s", BOOTSTRAP_JSON)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
