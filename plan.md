Here is the master technical blueprint. This is designed to be handed directly to a development team (or in this case, serve as your absolute source of truth) so that every single line of code written aligns perfectly with your professor's 7-point rubric. 

### Master Technical Blueprint: Regulation Alert System 2.0
**Project Objective:** Transform an existing Python/React legislative tracking platform into a generative AI legal simplification and semantic search engine, strictly fulfilling all Gen AI academic requirements.

---

#### 1. Architecture & Tech Stack Expansion
You are keeping your existing Flask and React setup. We are injecting the Machine Learning (ML) pipeline alongside it.

* **Frontend:** React 18, Vite, Recharts (Existing) + side-by-side text comparison components.
* **Backend:** Flask, SQLite (Existing) + **ChromaDB** (New: Vector DB for semantic search).
* **Gen AI Stack:**
    * **Data Generation:** Cloud LLM API (Gemini 1.5 Pro or GPT-4o) to create the training dataset.
    * **Fine-Tuning Framework:** Unsloth (highly recommended for fast, memory-efficient PEFT/QLoRA on free Colab GPUs), Hugging Face `transformers`, `peft`, `trl`.
    * **Base Model:** Llama-3-8B-Instruct or Mistral-7B-v0.3.
    * **Evaluation:** `evaluate` library (ROUGE, BLEU), `pandas` for error logging.
    * **Guardrails:** `NeMo-Guardrails` (or custom Python middleware).

---

#### 2. Phase-by-Phase Execution Plan

**Phase 1: Data Engineering & Dataset Curation (Rubric i, iv)**
* **The Goal:** Build the golden dataset for fine-tuning and populate the Vector DB.
* **Step 1.1 (Extraction):** Query the existing SQLite database. Pull a representative sample of ~500 documents, ensuring a mix of both parliamentary bills and established legislative acts.
* **Step 1.2 (Target Generation):** Write a Python script that loops through these 500 documents and sends the raw text to a high-tier Cloud API with a strict system prompt: *"You are an expert legal translator. Summarize this Indian legislative text into plain, accessible English suitable for a high school reading level. Retain all factual penalties, dates, and jurisdictions."*
* **Step 1.3 (Structuring):** Save the output as a `.jsonl` file formatted for instruction tuning: `{"instruction": "Simplify this legal text", "input": "[RAW ACT/BILL]", "output": "[API GENERATED SUMMARY]"}`.
* **Step 1.4 (Splitting):** Randomly split the JSONL into `train.jsonl` (80%), `val.jsonl` (10%), and `test.jsonl` (10%).
* **Step 1.5 (Vectorization):** Implement a standard RAG (Retrieval-Augmented Generation) pipeline. Chunk the raw texts, generate embeddings, and load them into ChromaDB to enable semantic search queries.

**Phase 2: Model Fine-Tuning [PEFT] (Rubric ii)**
* **The Goal:** Train a smaller open-weights model to mimic the high-tier API's simplification style.
* **Step 2.1 (Environment):** Set up a Google Colab notebook with a T4 or A100 GPU. 
* **Step 2.2 (Training Setup):** Load the base model in 4-bit quantization. Apply LoRA adapters targeting the attention modules (`q_proj`, `v_proj`).
* **Step 2.3 (Execution):** Train the model on `train.jsonl` using the `SFTTrainer`. 
* **Step 2.4 (Export):** Merge the LoRA weights with the base model and export the final model/adapter to Hugging Face or save it locally. Document the exact hyperparameters used (learning rate, batch size, epoch count) for the final report to justify the PEFT approach.

**Phase 3: Evaluation & Baseline Testing (Rubric iii, v)**
* **The Goal:** Prove mathematically that the fine-tuning worked.
* **Step 3.1 (Baseline Generation):** Feed the inputs from `test.jsonl` into the raw, un-tuned base model using standard prompt engineering. Save the outputs.
* **Step 3.2 (Fine-Tuned Generation):** Feed the exact same inputs into your new PEFT model. Save the outputs.
* **Step 3.3 (Metrics Calculation):** Run a Python script comparing both sets of outputs against the "golden" target summaries from your test set using ROUGE-1, ROUGE-L, and BLEU metrics. Generate a CSV report showing the delta.

**Phase 4: Backend Integration & Guardrails (Rubric vi)**
* **The Goal:** Connect the ML model to Flask and make it safe for real-world use.
* **Step 4.1 (Flask Updates):** Rewrite `ai_service.py` to route summarization requests to your fine-tuned model. 
* **Step 4.2 (Input Guardrails):** Add a middleware layer that checks the user's search/prompt. If the semantic distance indicates the query is non-legal (e.g., "write a story"), intercept and return a standardized error.
* **Step 4.3 (Output Guardrails):** Append a mandatory legal disclaimer to all generated text. 
* **Step 4.4 (Sentiment & Analytics):** Re-integrate the sentiment analysis of the legislation to run alongside the summary generation, providing a holistic view of the bill's impact.
* **Step 4.5 (Error Analysis Logging):** Create a dedicated `failure_cases.md` log during testing to manually record at least 10 instances of model hallucination or dropped context for the final submission.

**Phase 5: Frontend UI Polish (Rubric vii, Desired UI)**
* **The Goal:** Demonstrate real-world applicability through a clean interface.
* **Step 5.1:** Update the React search bar to query the Vector DB endpoint instead of the standard SQLite text-match endpoint.
* **Step 5.2:** Design a "Document View" page featuring a split-screen or toggle: "Original Legal Text" vs. "AI Simplified Summary".
* **Step 5.3:** Display the text's sentiment analysis score prominently next to the AI summary.

---

#### 3. Updated Project Folder Structure
This shows exactly where your new ML tasks fit into the existing repository.

```text
VidhanAi/
├── backend/
│   ├── app.py
│   ├── routes.py
│   ├── ai_service.py         # UPDATED: Now interfaces with the tuned model & Vector DB
│   ├── db_service.py
│   ├── instance/
│   │   ├── sqlite.db         # Existing: Relational metadata
│   │   └── chroma_db/        # NEW: Vector embeddings for semantic search
│   └── scripts/
│       ├── setup/
│       └── ml_pipeline/      # NEW FOLDER: All Gen AI coursework goes here
│           ├── 1_generate_dataset.py
│           ├── 2_vectorize_docs.py
│           ├── 3_calculate_metrics.py
│           └── datasets/
│               ├── train.jsonl
│               ├── val.jsonl
│               └── test.jsonl
├── frontend/                 # Existing React App
├── notebooks/                # NEW FOLDER: For model training
│   └── qlora_finetuning.ipynb 
└── docs/
    ├── PROJECT_TECH_STACK.md
    └── GEN_AI_EVALUATION.md  # NEW: Contains ROUGE scores, baseline comparisons, and error analysis logs
```

---

This blueprint serves as a complete map to secure full marks. Which of these five phases should we focus on first to start writing the actual code?