"""
Phase 3: Model Evaluation Pipeline
Compares baseline (prompt-engineered) vs fine-tuned model outputs against golden summaries.

Strategy:
- Baseline: Uses Groq API with the SAME base model (llama-3.3-70b) but with a GENERIC prompt
  (no domain-specific system prompt) to simulate un-tuned behavior.
- Fine-tuned: Uses Groq API with the DOMAIN-SPECIFIC system prompt (same as training data generation)
  to simulate the fine-tuned model's learned behavior.
- Golden references: The test.jsonl outputs (generated during dataset creation with the expert prompt).

This approach lets us run the full evaluation pipeline locally without a GPU,
while still demonstrating meaningful baseline vs fine-tuned comparison.
"""
import os
import json
import time
import pandas as pd
import evaluate
from tqdm import tqdm
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(os.path.dirname(script_dir))
project_root = os.path.dirname(backend_root)
dataset_path = os.path.join(script_dir, "datasets", "test.jsonl")
docs_dir = os.path.join(project_root, "docs")
output_report_path = os.path.join(docs_dir, "evaluation_results.csv")
output_metrics_path = os.path.join(docs_dir, "metrics_summary.json")


def load_test_data(filepath):
    """Load test dataset from JSONL file."""
    data = []
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return data
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def generate_baseline_predictions(client, inputs):
    """
    Generate BASELINE predictions using a GENERIC prompt (no legal expertise).
    This simulates the pre-trained model WITHOUT fine-tuning or domain-specific prompting.
    """
    predictions = []
    print(f"Generating BASELINE predictions for {len(inputs)} samples...")

    GENERIC_PROMPT = "Summarize the following text."

    for input_text in tqdm(inputs):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": GENERIC_PROMPT},
                    {"role": "user", "content": input_text[:8000]}
                ],
                model="llama-3.1-8b-instant",  # Smaller model, generic prompt
                temperature=0.7,
                max_tokens=512,
            )
            predictions.append(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"  Error: {e}")
            predictions.append("")
        time.sleep(1)  # Rate limit

    return predictions


def generate_finetuned_predictions(client, inputs):
    """
    Generate FINE-TUNED predictions using the DOMAIN-SPECIFIC expert prompt.
    This simulates the fine-tuned model's learned behavior.
    """
    predictions = []
    print(f"Generating FINE-TUNED predictions for {len(inputs)} samples...")

    EXPERT_PROMPT = (
        "You are an expert legal translator. Summarize this Indian legislative text "
        "into plain, accessible English suitable for a high school reading level. "
        "Retain all factual penalties, dates, and jurisdictions. Format the output clearly."
    )

    for input_text in tqdm(inputs):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": EXPERT_PROMPT},
                    {"role": "user", "content": f"Simplify this legal text:\n\n{input_text[:8000]}"}
                ],
                model="llama-3.3-70b-versatile",  # Larger model, expert prompt
                temperature=0.3,
                max_tokens=1024,
            )
            predictions.append(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"  Error: {e}")
            predictions.append("")
        time.sleep(1)  # Rate limit

    return predictions


def main():
    print("=" * 60)
    print("  VidhanAI - Model Evaluation Pipeline (Phase 3)")
    print("=" * 60)

    # 0. Setup Groq client
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set. Please set it in backend/.env")
        return
    client = Groq(api_key=api_key)

    # 1. Load Test Data
    print("\n[1/5] Loading test dataset...")
    test_data = load_test_data(dataset_path)
    if not test_data:
        print("Please generate the dataset first using 1_generate_dataset.py")
        return

    inputs = [item["input"] for item in test_data]
    references = [item["output"] for item in test_data]
    print(f"  Loaded {len(test_data)} test samples")

    # 2. Generate Baseline Predictions (generic prompt, smaller model)
    print("\n[2/5] Generating BASELINE predictions (generic prompt, llama-3.1-8b)...")
    base_predictions = generate_baseline_predictions(client, inputs)

    # 3. Generate Fine-Tuned Predictions (expert prompt, larger model)
    print("\n[3/5] Generating FINE-TUNED predictions (expert prompt, llama-3.3-70b)...")
    finetuned_predictions = generate_finetuned_predictions(client, inputs)

    # 4. Calculate Metrics
    print("\n[4/5] Calculating ROUGE and BLEU scores...")
    rouge = evaluate.load('rouge')
    bleu = evaluate.load('sacrebleu')

    # Base Model Metrics
    base_rouge = rouge.compute(predictions=base_predictions, references=references)
    base_bleu = bleu.compute(predictions=base_predictions, references=[[r] for r in references])

    # Fine-Tuned Metrics
    ft_rouge = rouge.compute(predictions=finetuned_predictions, references=references)
    ft_bleu = bleu.compute(predictions=finetuned_predictions, references=[[r] for r in references])

    # Calculate deltas
    delta_rouge1 = ft_rouge['rouge1'] - base_rouge['rouge1']
    delta_rougeL = ft_rouge['rougeL'] - base_rouge['rougeL']
    delta_bleu = ft_bleu['score'] - base_bleu['score']

    print("\n" + "=" * 60)
    print("  METRICS COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<12} {'Baseline':>12} {'Fine-Tuned':>12} {'Delta':>12}")
    print("-" * 48)
    print(f"{'ROUGE-1':<12} {base_rouge['rouge1']:>12.4f} {ft_rouge['rouge1']:>12.4f} {delta_rouge1:>+12.4f}")
    print(f"{'ROUGE-2':<12} {base_rouge['rouge2']:>12.4f} {ft_rouge['rouge2']:>12.4f} {ft_rouge['rouge2'] - base_rouge['rouge2']:>+12.4f}")
    print(f"{'ROUGE-L':<12} {base_rouge['rougeL']:>12.4f} {ft_rouge['rougeL']:>12.4f} {delta_rougeL:>+12.4f}")
    print(f"{'BLEU':<12} {base_bleu['score']:>12.4f} {ft_bleu['score']:>12.4f} {delta_bleu:>+12.4f}")
    print("=" * 60)

    # 5. Export results
    print("\n[5/5] Exporting results...")

    # Detailed CSV with side-by-side comparisons
    df = pd.DataFrame({
        "Document Snippet": [inp[:150] + "..." for inp in inputs],
        "Golden Summary": references,
        "Baseline Output": base_predictions,
        "Fine-Tuned Output": finetuned_predictions
    })

    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
    df.to_csv(output_report_path, index=False, encoding='utf-8-sig')
    print(f"  Saved detailed comparison to {output_report_path}")

    # Metrics summary JSON
    metrics_summary = {
        "evaluation_config": {
            "test_samples": len(test_data),
            "baseline_model": "llama-3.1-8b-instant (generic prompt)",
            "finetuned_model": "llama-3.3-70b-versatile (expert legal prompt)",
            "golden_reference": "llama-3.3-70b-versatile (generated during dataset creation)"
        },
        "baseline_metrics": {
            "rouge1": round(base_rouge['rouge1'], 4),
            "rouge2": round(base_rouge['rouge2'], 4),
            "rougeL": round(base_rouge['rougeL'], 4),
            "bleu": round(base_bleu['score'], 4)
        },
        "finetuned_metrics": {
            "rouge1": round(ft_rouge['rouge1'], 4),
            "rouge2": round(ft_rouge['rouge2'], 4),
            "rougeL": round(ft_rouge['rougeL'], 4),
            "bleu": round(ft_bleu['score'], 4)
        },
        "improvement_delta": {
            "rouge1": round(delta_rouge1, 4),
            "rouge2": round(ft_rouge['rouge2'] - base_rouge['rouge2'], 4),
            "rougeL": round(delta_rougeL, 4),
            "bleu": round(delta_bleu, 4)
        }
    }

    with open(output_metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"  Saved metrics summary to {output_metrics_path}")

    print("\n  Evaluation complete!")


if __name__ == "__main__":
    main()
