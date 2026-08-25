"""
VidhanAI - Standalone LoRA evaluation (Kaggle-ready).

Use this to run the *real* evaluation: zero-shot Llama-3.2-3B-Instruct vs.
the fine-tuned LoRA adapter on the held-out test split. Designed for one
Kaggle notebook cell: paste the entire file and run.

Kaggle layout it expects:
    /kaggle/input/<OWNER>/<DATASET_SLUG>/test.jsonl      # test split
    /kaggle/input/<OWNER>/<DATASET_SLUG>/train.jsonl     # (unused here)
    /kaggle/input/<OWNER>/vidhanai-lora/adapter_config.json
    /kaggle/input/<OWNER>/vidhanai-lora/adapter_model.safetensors
    ... (chat_template.jinja, tokenizer files)

Output:
    /kaggle/working/metrics_summary.json
    /kaggle/working/evaluation_results.csv
    /kaggle/working/metrics_bootstrap.json
"""
from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

# Paths the user can override
TEST_JSONL   = Path(os.environ.get("VIDHANAI_TEST",   "/kaggle/input/deathgate99/vidhanai/test.jsonl"))
ADAPTER_DIR  = Path(os.environ.get("VIDHANAI_LORA_DIR", "/kaggle/input/deathgate99/vidhanai-lora"))
OUT_DIR      = Path("/kaggle/working")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_MODEL      = "unsloth/Llama-3.2-3B-Instruct"  # non-quantized so no bitsandbytes needed at inference
MAX_SEQ_LEN     = 2048
MAX_NEW_TOKENS  = 384
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED      = 42

EXPERT_SYSTEM_PROMPT = (
    "You are an expert legal translator. Summarize this Indian legislative "
    "text into plain, accessible English suitable for a high school reading "
    "level. Retain all factual penalties, dates, and jurisdictions. Format "
    "the output clearly with headings and bullet points. Do not include "
    "meta-commentary about your approach, notes to the reader, or headings "
    "such as 'Here is the summary' / 'How I approached this'."
)
INSTRUCTION = "Simplify this legal text"

# ---------------------------------------------------------------------------
# Imports (kept in-band so this can run as a single notebook cell)
# ---------------------------------------------------------------------------
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

try:
    import evaluate
    EVALUATE_AVAILABLE = True
except ImportError:
    EVALUATE_AVAILABLE = False
    raise SystemExit("Install evaluate, rouge_score, sacrebleu first "
                     "(`pip install evaluate rouge_score sacrebleu`).")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(p: Path):
    rows = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def make_prompt(tokenizer, user_text: str) -> str:
    messages = [
        {"role": "system", "content": EXPERT_SYSTEM_PROMPT},
        {"role": "user",   "content": f"{INSTRUCTION}:\n\n{user_text}"},
    ]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )


def generate(model, tokenizer, prompts):
    preds = []
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                           max_length=MAX_SEQ_LEN).to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=0.3,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = outputs[0][inputs.input_ids.shape[1]:]
        preds.append(tokenizer.decode(new_tokens, skip_special_tokens=True).strip())
    return preds


def compute_metrics(preds, refs):
    rouge = evaluate.load("rouge")
    bleu  = evaluate.load("sacrebleu")
    r = rouge.compute(predictions=preds, references=refs)
    b = bleu.compute(predictions=preds, references=[[r] for r in refs])["score"]
    return {
        "rouge1": round(float(r["rouge1"]), 4),
        "rouge2": round(float(r["rouge2"]), 4),
        "rougeL": round(float(r["rougeL"]), 4),
        "bleu":   round(float(b), 4),
    }


def bootstrap_ci(preds, refs, n_resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    if len(preds) != len(refs) or len(preds) < 2:
        return {"mean": None, "ci_low": None, "ci_high": None}
    rnd = random.Random(seed)
    n = len(preds)
    sampled = []
    for _ in range(n_resamples):
        idx = [rnd.randrange(n) for _ in range(n)]
        sampled.append(compute_metrics([preds[i] for i in idx],
                                       [refs[i]  for i in idx]))
    names = sampled[0].keys()
    return {
        name: {
            "mean":   round(statistics.mean(m[name] for m in sampled), 4),
            "ci_low": round(sorted(m[name] for m in sampled)[int(0.025 * n_resamples)], 4),
            "ci_high": round(sorted(m[name] for m in sampled)[int(0.975 * n_resamples) - 1], 4),
            "median": round(statistics.median(m[name] for m in sampled), 4),
        }
        for name in names
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[{time.strftime('%H:%M:%S')}] Loading {BASE_MODEL} in fp16 ...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map="auto",
        low_cpu_mem_usage=True,
    )

    print(f"[{time.strftime('%H:%M:%S')}] Loading test set from {TEST_JSONL}")
    test_rows = load_jsonl(TEST_JSONL)
    if not test_rows:
        raise SystemExit(f"No test rows found at {TEST_JSONL}")
    inputs  = [r["input"] for r in test_rows]
    refs    = [r["output"] for r in test_rows]
    bill_ids = [r.get("bill_id", "?") for r in test_rows]
    prompts = [make_prompt(tokenizer, t) for t in inputs]
    print(f"  {len(test_rows)} test samples loaded")

    print(f"\n[{time.strftime('%H:%M:%S')}] === BASELINE (zero-shot Llama-3.2-3B) ===")
    base_preds = generate(model, tokenizer, prompts)

    print(f"\n[{time.strftime('%H:%M:%S')}] === FINE-TUNED (LoRA adapter) ===")
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()
    ft_preds = generate(model, tokenizer, prompts)

    # Unload adapter to free memory before metrics
    del model
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    print(f"\n[{time.strftime('%H:%M:%S')}] Computing ROUGE/BLEU ...")
    base_metrics = compute_metrics(base_preds, refs)
    ft_metrics   = compute_metrics(ft_preds, refs)
    delta        = {k: round(ft_metrics[k] - base_metrics[k], 4)
                    for k in base_metrics}

    print(f"\n  Baseline: {base_metrics}")
    print(f"  Fine-Tuned: {ft_metrics}")
    print(f"  Delta: {delta}")

    print(f"\n[{time.strftime('%H:%M:%S')}] Bootstrap CIs ({BOOTSTRAP_RESAMPLES} resamples) ...")
    base_ci = bootstrap_ci(base_preds, refs)
    ft_ci   = bootstrap_ci(ft_preds, refs)

    summary = {
        "evaluation_config": {
            "test_samples": len(test_rows),
            "baseline_model": BASE_MODEL + " (zero-shot, expert prompt)",
            "finetuned_model": f"LoRA-on-{BASE_MODEL} (r=16, alpha=16, lr=2e-4)",
            "adapter_dir": str(ADAPTER_DIR),
            "golden_reference": "groq/compound (expert legal prompt) — see docs/metrics_summary.json",
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "baseline_metrics": base_metrics,
        "finetuned_metrics": ft_metrics,
        "improvement_delta": delta,
        "bootstrap": {"baseline": base_ci, "finetuned": ft_ci},
    }

    # CSV
    csv_path = OUT_DIR / "evaluation_results.csv"
    with csv_path.open("w", encoding="utf-8-sig") as fh:
        fh.write("bill_id,Document Snippet,Golden Summary,Baseline Output,Fine-Tuned Output\n")
        for i in range(len(test_rows)):
            snip = inputs[i][:150].replace('"', '""')
            gold = refs[i].replace('"', '""')
            base = base_preds[i].replace('"', '""')
            ft = ft_preds[i].replace('"', '""')
            fh.write(f'"{bill_ids[i]}","{snip}...","{gold}","{base}","{ft}"\n')

    (OUT_DIR / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"\n[{time.strftime('%H:%M:%S')}] Wrote:")
    print(f"  {csv_path}")
    print(f"  {OUT_DIR / 'metrics_summary.json'}")
    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
