"""
Phase 1 - Reproducible dataset generation for the VidhanAI summarization pipeline.

Goals (from PHASE1_STATUS.md):
    * Read source bill text from the local SQLite database, not from live PRS
      scraping, so the same run on the same DB always yields the same dataset.
    * Produce >=100 instruction samples with a deterministic 80/10/10 split.
    * Resume safely: cache each LLM-generated row to JSONL as it lands so an
      interrupted run can pick up where it left off.
    * Validate the {instruction, input, output} schema per row.
    * Accept --num-samples, --output-dir, --db-path flags.

Outputs land in ``backend/scripts/ml_pipeline/datasets/``:
    * train.jsonl, val.jsonl, test.jsonl
    * generation_log.jsonl (one entry per LLM call, for auditability)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:  # pragma: no cover
    GROQ_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:  # pragma: no cover
    TQDM_AVAILABLE = False


# ---------------------------------------------------------------------------
# Paths & configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "datasets"
BACKEND_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_DB_PATH = BACKEND_ROOT / "instance" / "regulation_alert.db"
DEFAULT_ENV_PATH = BACKEND_ROOT / ".env"

EXPERT_SYSTEM_PROMPT = (
    "You are an expert legal translator. Summarize this Indian legislative "
    "text into plain, accessible English suitable for a high school reading "
    "level. Retain all factual penalties, dates, and jurisdictions. Format "
    "the output clearly with headings and bullet points. Do not include "
    "meta-commentary about your approach, notes to the reader, or headings "
    "such as 'Here is the summary' / 'How I approached this'."
)

INSTRUCTION = "Simplify this legal text"

# A sample is only useful if the bill text is long enough to actually train on.
MIN_TEXT_CHARS = 500
MAX_TEXT_CHARS = 5000  # Trim long bills so the dataset stays compact.

TRAIN_RATIO = 0.8
VAL_RATIO = 0.1  # Test ratio is implicit: 1 - TRAIN - VAL.

# Resume on partial completion unless --no-resume is passed.
RESUME_BY_DEFAULT = True


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("vidhanai.generate_dataset")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# ---------------------------------------------------------------------------
# Database access
# ---------------------------------------------------------------------------

def _import_models():
    """Import the SQLAlchemy models without requiring the Flask app to be running."""
    sys.path.insert(0, str(BACKEND_ROOT))
    from models import db, Bill, BillContent  # type: ignore  # noqa: WPS433
    return db, Bill, BillContent


def load_bills_with_content(db_path: Path):
    """Yield (bill_id, title, full_text) tuples from the local SQLite DB."""
    from flask import Flask

    db, Bill, BillContent = _import_models()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        rows = (
            db.session.query(Bill, BillContent)
            .join(BillContent, Bill.id == BillContent.bill_id)
            .filter(BillContent.full_text.isnot(None))
            .all()
        )

    for bill, content in rows:
        yield bill.bill_id, bill.title, content.full_text or ""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _get_groq_client():
    if not GROQ_AVAILABLE:
        raise RuntimeError("groq package not installed; run `pip install groq`.")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Export it before running this script."
        )
    # The free tier is ~30 RPM. High max_retries turns transient 429s into
    # small waits rather than dropped samples (each retry costs a few seconds,
    # far cheaper than re-fetching the source bill).
    return Groq(api_key=api_key, max_retries=8)


def generate_summary(client, text: str, model: str) -> str | None:
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": EXPERT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Simplify this legal text:\n\n{text[:15000]}"},
            ],
            model=model,
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as exc:  # pragma: no cover - network/api
        logger.warning("Groq call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_row(row: dict) -> bool:
    if not isinstance(row, dict):
        return False
    for key in ("instruction", "input", "output"):
        if key not in row or not isinstance(row[key], str):
            return False
    if not row["input"].strip() or not row["output"].strip():
        return False
    return True


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def _load_cache(cache_path: Path) -> dict[str, dict]:
    if not cache_path.exists():
        return {}
    cache: dict[str, dict] = {}
    with cache_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            bill_id = row.get("bill_id")
            if bill_id and _validate_row(row):
                cache[bill_id] = row
    return cache


def _append_cache(cache_path: Path, row: dict) -> None:
    with cache_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-samples", type=int, default=120,
                        help="Target number of instruction samples to produce.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--model", type=str,
                        default=os.environ.get("VIDHANAI_GROQ_MODEL", "groq/compound"),
                        help="Groq teacher model (default: groq/compound).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-resume", action="store_true",
                        help="Don't reuse rows from a previous partial run.")
    parser.add_argument("--min-text-chars", type=int, default=MIN_TEXT_CHARS)
    parser.add_argument("--max-text-chars", type=int, default=MAX_TEXT_CHARS)
    return parser.parse_args()


def collect_eligible_bills(db_path: Path, min_chars: int) -> list[tuple[str, str, str]]:
    bills = []
    for bill_id, title, full_text in load_bills_with_content(db_path):
        if len(full_text) >= min_chars:
            bills.append((bill_id, title, full_text))
    return bills


def write_splits(dataset: list[dict], output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(dataset)
    train_end = int(total * TRAIN_RATIO)
    val_end = train_end + int(total * VAL_RATIO)
    splits = {
        "train.jsonl": dataset[:train_end],
        "val.jsonl": dataset[train_end:val_end],
        "test.jsonl": dataset[val_end:],
    }
    counts = {}
    for filename, rows in splits.items():
        path = output_dir / filename
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[filename] = len(rows)
    return counts


def main() -> int:
    args = parse_args()

    if load_dotenv is not None and DEFAULT_ENV_PATH.exists():
        load_dotenv(DEFAULT_ENV_PATH)

    random.seed(args.seed)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / "generation_log.jsonl"

    if not args.db_path.exists():
        logger.error("Database not found at %s", args.db_path)
        logger.error("Run backend/scripts/setup/init_db.py and populate bills first.")
        return 1

    if not GROQ_AVAILABLE:
        logger.error("groq package missing. Install with: pip install groq")
        return 1

    eligible = collect_eligible_bills(args.db_path, args.min_text_chars)
    logger.info("Found %d bills with full text >= %d chars.", len(eligible), args.min_text_chars)

    if len(eligible) < args.num_samples:
        logger.warning(
            "Only %d eligible bills available, target was %d. Will use what we have.",
            len(eligible), args.num_samples,
        )

    target_count = min(args.num_samples, len(eligible))
    selected = random.sample(eligible, target_count) if target_count else []

    cache: dict[str, dict] = _load_cache(cache_path) if (RESUME_BY_DEFAULT and not args.no_resume) else {}
    if cache:
        logger.info("Resuming from cache with %d already-generated rows.", len(cache))

    # Skip bills we already have cached for.
    todo = [(bid, title, text) for (bid, title, text) in selected if bid not in cache]
    logger.info("Need to generate %d new rows.", len(todo))

    client = _get_groq_client()
    iterator = tqdm(todo, desc="Generating summaries") if TQDM_AVAILABLE else todo
    for bill_id, title, full_text in iterator:
        truncated = full_text[: args.max_text_chars]
        summary = generate_summary(client, truncated, args.model)
        if not summary:
            logger.warning("Skipping %s (no summary returned).", bill_id)
            continue
        row = {
            "bill_id": bill_id,
            "title": title,
            "instruction": INSTRUCTION,
            "input": truncated,
            "output": summary,
            "model_version": args.model,
            "generated_at": datetime.utcnow().isoformat(),
        }
        if not _validate_row(row):
            logger.warning("Row failed schema validation for %s, skipping.", bill_id)
            continue
        cache[bill_id] = row
        _append_cache(cache_path, row)
        # Free tier is ~30 RPM: ~3.5s spacing keeps us comfortably under (no
        # retry storms). max_retries=8 on the client absorbs transient spikes.
        time.sleep(3.5)

    dataset = list(cache.values())
    random.shuffle(dataset)
    counts = write_splits(dataset, output_dir)
    logger.info("Wrote dataset splits: %s", counts)
    logger.info("Total cached rows: %d", len(dataset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
