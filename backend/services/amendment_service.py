"""
VidhanAI amendment-diff service.

Phase 3 / Step 3 - "Delta-aware legislative summarization" (the proposal's
stated new research contribution).

What this does:
    Given two bill texts (v1, v2), it returns a structured diff:
        - added sections: present in v2, absent in v1
        - removed sections: present in v1, absent in v2
        - modified sections: same heading in both, materially different content
        - changed facts: penalty/dates/amounts that moved (regex-based)

The structural diff is pure-Python (no LLM cost, deterministic, reproducible).
The *narrative* around the diff is delegated to the existing LLM Service
(via ai_service.generate_change_narrative).
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Section parsing
# ---------------------------------------------------------------------------
#
# Indian bill structure is heterogeneous (PRS HTML scrapes don't always give us
# numbered sections), so we fall back to a header heuristic: any paragraph
# whose first non-blank token is "Section", "Chapter", "CHAPTER", or matches
# a numbered-clause pattern like "3.", "(a)", "Article 21".
#
# When the bill_content.sections JSON column is present and well-formed, we
# use that directly (it's already a list of {section, content} dicts).

SECTION_HEADER_PATTERNS = [
    re.compile(r"^\s*Section\s+\d+[A-Z]?\.?", re.IGNORECASE),
    re.compile(r"^\s*CHAPTER\s+[IVXLC]+", re.IGNORECASE),
    re.compile(r"^\s*Article\s+\d+[A-Z]?\.?", re.IGNORECASE),
    re.compile(r"^\s*\d+\.\s+[A-Z]"),  # "3. Definitions"
    re.compile(r"^\s*\([a-z]\)\s+[A-Z]"),
]


def _is_section_header(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    return any(p.match(line) for p in SECTION_HEADER_PATTERNS)


def split_into_sections(text: str) -> list[dict[str, str]]:
    """Split bill text into [{title, content}, ...] using header heuristics.

    Falls back to treating the whole text as one section if no headers found.
    """
    if not text:
        return []

    lines = text.splitlines()
    sections: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    def _flush():
        if current_lines or current_title:
            content = "\n".join(current_lines).strip()
            sections.append({"title": current_title.strip(), "content": content})

    for line in lines:
        if _is_section_header(line):
            _flush()
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    _flush()

    # If we got no headers, treat the whole text as one anonymous section so
    # we still produce a diff.
    if not sections:
        sections = [{"title": "(full text)", "content": text.strip()}]
    elif len(sections) == 1 and not sections[0]["title"]:
        sections[0]["title"] = "(full text)"

    return sections


# ---------------------------------------------------------------------------
# Section similarity (for "modified" detection)
# ---------------------------------------------------------------------------

def _shingles(text: str, k: int = 5) -> set[str]:
    """Return k-word shingles of ``text`` for Jaccard similarity."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 1.0


# Threshold for "modified": below this Jaccard similarity, the section
# counts as substantially different.
MODIFIED_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Fact extraction (penalties, dates, amounts)
# ---------------------------------------------------------------------------

FACT_PATTERNS = [
    re.compile(r"Rs\.?\s?\d[\d,]*\s*(?:crore|lakh|thousand|hundred|million)?", re.IGNORECASE),
    re.compile(r"₹\s?\d[\d,]*", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|"
               r"July|August|September|October|November|December)\b",
               re.IGNORECASE),
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\bimprisonment\s+(?:of\s+)?(?:up\s+to\s+)?\d+\s+(?:years|months)",
               re.IGNORECASE),
]


def extract_facts(text: str) -> set[str]:
    """Return the set of penalty/date/amount claims present in ``text``."""
    facts: set[str] = set()
    for pat in FACT_PATTERNS:
        for m in pat.findall(text):
            facts.add(m.strip())
    return facts


# ---------------------------------------------------------------------------
# Main diff entry point
# ---------------------------------------------------------------------------

def diff_bills(text_v1: str, text_v2: str,
               title_v1: str = "v1", title_v2: str = "v2") -> dict[str, Any]:
    """Compute a structural + factual diff between two bill texts.

    Returns:
        {
            "title_v1": str,
            "title_v2": str,
            "added_sections":    [{"title": str, "content": str}],
            "removed_sections":  [{"title": str, "content": str}],
            "modified_sections": [
                {"title": str,
                 "old_content": str,
                 "new_content": str,
                 "similarity": float,
                 "changed_facts": [str, ...]}
            ],
            "all_changed_facts": [str, ...],   # union across all sections
            "stats": {
                "v1_sections": int,
                "v2_sections": int,
                "added": int,
                "removed": int,
                "modified": int,
                "facts_added": int,
                "facts_removed": int,
            }
        }
    """
    s1 = split_into_sections(text_v1 or "")
    s2 = split_into_sections(text_v2 or "")

    # Index v1 sections by title (case-folded) for fast lookup.
    by_title_v1: dict[str, dict[str, str]] = {}
    for sec in s1:
        key = sec["title"].lower().strip()
        if not key:
            continue
        # Keep first occurrence per title (later duplicates ignored)
        by_title_v1.setdefault(key, sec)

    added: list[dict[str, str]] = []
    modified: list[dict[str, Any]] = []
    matched_v2_keys: set[str] = set()

    for sec2 in s2:
        key = sec2["title"].lower().strip()
        if not key:
            continue
        matched_v2_keys.add(key)
        if key not in by_title_v1:
            added.append({"title": sec2["title"], "content": sec2["content"]})
            continue

        # Same heading - check similarity
        sec1 = by_title_v1[key]
        sim = _jaccard(_shingles(sec1["content"]), _shingles(sec2["content"]))
        if sim < MODIFIED_THRESHOLD:
            facts1 = extract_facts(sec1["content"])
            facts2 = extract_facts(sec2["content"])
            changed = sorted((facts2 - facts1) | {f"-> {f}" for f in (facts1 - facts2)})
            modified.append({
                "title": sec2["title"],
                "old_content": sec1["content"],
                "new_content": sec2["content"],
                "similarity": round(sim, 3),
                "changed_facts": changed,
            })

    removed = [
        {"title": sec["title"], "content": sec["content"]}
        for sec in s1
        if sec["title"].lower().strip() and sec["title"].lower().strip() not in matched_v2_keys
    ]

    facts_v1 = extract_facts(text_v1 or "")
    facts_v2 = extract_facts(text_v2 or "")
    facts_added = sorted(facts_v2 - facts_v1)
    facts_removed = sorted(facts_v1 - facts_v2)
    all_changed_facts = facts_added + [f"(removed) {f}" for f in facts_removed]

    return {
        "title_v1": title_v1,
        "title_v2": title_v2,
        "added_sections": added,
        "removed_sections": removed,
        "modified_sections": modified,
        "all_changed_facts": all_changed_facts,
        "facts_added": facts_added,
        "facts_removed": facts_removed,
        "stats": {
            "v1_sections": len(s1),
            "v2_sections": len(s2),
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "facts_added": len(facts_added),
            "facts_removed": len(facts_removed),
        },
    }


def diff_summary_text(diff: dict[str, Any]) -> str:
    """Render a human-readable summary of a diff (no LLM needed for this view).

    The LLM narrative is layered on top by generate_change_narrative().
    """
    stats = diff.get("stats", {})
    parts = [
        f"v1 had {stats.get('v1_sections',0)} section(s); v2 has {stats.get('v2_sections',0)}.",
        f"Added: {stats.get('added',0)} section(s).",
        f"Removed: {stats.get('removed',0)} section(s).",
        f"Modified: {stats.get('modified',0)} section(s).",
    ]
    if diff.get("facts_added"):
        parts.append("New figures: " + "; ".join(diff["facts_added"][:8]))
    if diff.get("facts_removed"):
        parts.append("Removed figures: " + "; ".join(diff["facts_removed"][:8]))
    return "\n".join(parts)