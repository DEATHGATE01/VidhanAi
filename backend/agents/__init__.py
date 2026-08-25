"""
VidhanAI multi-agent orchestration layer (Phase 3).

Architecture (per AIDEVOPS faculty checklist):

    Application Service       -> routes.py (Flask)
    Orchestration Layer       -> agents/orchestrator.py (Researcher agent)
    RAG/Retrieval Service     -> agents/tools/rag_tool.py    (ChromaDB semantic search)
    Embedding Service         -> agents/tools/embedding_tool.py  (sentence-transformers)
    Data/Knowledge Service    -> agents/tools/data_tool.py   (SQLite)
    LLM Service               -> agents/tools/llm_tool.py    (LoRA adapter + Groq fallback)
    Guardrail Service         -> agents/tools/guardrail_tool.py (input/output)
    API/Gateway Service       -> routes.py                   (existing)

This package exposes:
    - run_research(question, max_steps) -> CrewOutput
    - the list of registered tools (for /api/architecture inspection)

Run locally:
    cd backend && python -c "from agents import run_research; \
        out = run_research('Compare the 2023 Telecom Bill to the 2024 amendment'); \
        print(out.raw)"
"""
from __future__ import annotations

import logging

from .orchestrator import run_research, get_tool_inventory

logger = logging.getLogger(__name__)

__all__ = ["run_research", "get_tool_inventory"]
