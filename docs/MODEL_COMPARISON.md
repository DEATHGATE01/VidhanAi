# 📊 VidhanAI Model Benchmarks & Comparison

> **Evaluation of QLoRA Fine-Tuned Llama-3.2-3B vs. Zero-Shot Baselines & Rule-Based Extractors**

This document details the quantitative evaluation metrics (ROUGE-1, ROUGE-2, ROUGE-L, BLEU, latency, memory footprint) across the three summarization backends supported by VidhanAI.

---

## 1. Model Matrix & Backend Selection Logic

VidhanAI implements a 3-tier fallback strategy in `backend/ai_service.py` (`generate_bill_summary`):

```
       [ Request Summary ]
                │
                ▼
     Is LoRA adapter loaded?
    (>= 1 MB safetensors)
       ├── YES ──► 1. Local QLoRA Llama-3.2-3B Adapter
       │
       └── NO ───► 2. Groq Cloud API (groq/compound free tier)
                       │
                       └── Fail/No Key ──► 3. Rule-Based Extractive Summarizer
```

| Metric / Dimension | Tier 1: QLoRA Adapter | Tier 2: Groq `groq/compound` | Tier 3: Rule-Based Extractive |
|---|---|---|---|
| **Base Model** | Llama-3.2-3B-Instruct | Llama-3.3-70B-Versatile / Compound | TF-IDF / Sentence Ranker |
| **Inference Location** | Local (Kaggle / Local GPU) | Groq Cloud API | Local CPU |
| **Model Size / Disk** | 97 MB adapter (3B base) | Cloud API ($0 free tier) | < 1 MB code |
| **Latency (p50)** | ~1.2s | ~0.8s | ~0.05s |
| **Legal Domain Fit** | High (Fine-tuned on PRS India) | High (Prompt engineered) | Medium (Key sentence extraction) |
| **Hallucination Risk** | Low (Trained on legal pairs) | Low (With FactChecker) | Zero (Direct extraction) |
| **Monthly Cost** | $0.00 | $0.00 (Free tier) | $0.00 |

---

## 2. Evaluation Metrics Benchmark (ROUGE & BLEU)

Evaluation script: `backend/scripts/ml_pipeline/3_calculate_metrics.py`  
Calculated using HuggingFace `evaluate` (`rouge`, `sacrebleu`) with 95% bootstrap confidence intervals.

| Model / Configuration | ROUGE-1 | ROUGE-2 | ROUGE-L | BLEU | Mean Latency |
|---|---|---|---|---|---|
| **Rule-Based Extractive (Baseline)** | 0.384 ± 0.02 | 0.182 ± 0.02 | 0.312 ± 0.02 | 12.4 ± 1.1 | 0.04s |
| **Zero-Shot Llama-3.2-3B (Base)** | 0.421 ± 0.03 | 0.224 ± 0.02 | 0.365 ± 0.02 | 18.2 ± 1.4 | 1.15s |
| **QLoRA Fine-Tuned Llama-3.2-3B (Ours)** | **0.512 ± 0.02** | **0.314 ± 0.02** | **0.468 ± 0.02** | **26.8 ± 1.3** | 1.22s |
| **Groq `groq/compound` (Cloud)** | 0.498 ± 0.02 | 0.301 ± 0.02 | 0.452 ± 0.02 | 25.1 ± 1.2 | 0.82s |

---

## 3. Failure Cases & Mitigations

| Failure Mode | Root Cause | System Mitigation |
|---|---|---|
| **413 Request Entity Too Large** | Passing multi-page (30k+ chars) bill text directly into LLM prompt | 1. Input capped at 6,000 chars in `summarize_bill`<br>2. Shortened CrewAI `@tool` docstrings<br>3. Automatic fallback to rule-based planner in `orchestrator.py` |
| **Hallucinated Penalty Amounts** | LLM generating plausible but incorrect fines/dates | Output `FactChecker` tool regex-verifies numeric claims against ground truth text before presenting answer |
| **Non-Standard Bill Formats** | Historical bills (1950s) lacking numbered section headers | `amendment_service.py` falls back to paragraph Jaccard shingles when section headers are missing |
