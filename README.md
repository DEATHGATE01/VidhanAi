# 🏛️ VidhanAI — Generative AI Legislative Simplification Engine

> **A Service-Oriented Multi-Agent Intelligence Engine for Indian Legislation**  
> *QLoRA Fine-Tuned Llama-3.2-3B · CrewAI Multi-Agent Orchestration · ChromaDB Semantic RAG · Delta-Aware Amendment Summarization*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.8.1-purple.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 System Overview

**VidhanAI** is an end-to-end AI system that transforms complex Indian parliamentary legislation (PRS India BillTrack database) into simplified, accessible, and grounded plain-English summaries.

### 🎯 Key Research Contributions & Features

1. ⚖️ **Delta-Aware Amendment Summarization** (Primary Proposal Contribution): Structural section diffing (`added`, `removed`, `modified`) + factual figure tracking (penalties, dates, amounts) layered with LLM change narratives.
2. 🤖 **QLoRA Fine-Tuned Model**: 97 MB safetensors adapter fine-tuned on Llama-3.2-3B for legal simplification (evaluated against zero-shot baselines with ROUGE/BLEU).
3. 🧠 **CrewAI Multi-Agent Orchestration**: 7 specialist tools wrapping independent microservices (`bill_lookup`, `semantic_search`, `summarize_bill`, `check_input_safe`, `fact_check`, `amendment_diff`, `citation_finder`).
4. 🔍 **ChromaDB Vector RAG**: 12,000+ vector embeddings (`all-MiniLM-L6-v2`) for semantic passage retrieval.
5. 🛡️ **Dual-Stage Guardrails**: Input injection filter + output FactChecker for numeric claim verification.
6. 📰 **CitationFinder / News Citation**: Real-time media coverage & PRS citation links via RSS ($0 cost).
7. 💸 **Free Tier Architecture**: Designed for $0/month deployment (Render + Vercel free tiers).

---

## 🏗️ Architecture

```
                                  [ User Browser ]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [ Vercel Frontend ]                           [ Render Backend ]
      Vite React 18 App                              Flask WSGI Server
      Port: 5173 (Dev)                               Port: 5000 (API)
                   │                                           │
                   └──────────────► REST API ◄─────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         [ CrewAI Orchestration ]             [ Data & Storage ]
         Researcher Agent                     ├─ SQLite DB (11 Tables)
         ├─ check_input_safe                  ├─ ChromaDB Vector DB
         ├─ bill_lookup                       └─ LoRA Weights (97 MB)
         ├─ semantic_search
         ├─ summarize_bill
         ├─ fact_check
         ├─ amendment_diff
         └─ citation_finder
```

---

## ⚡ Quick Start (Local Development)

Launch both backend (Flask :5000) and frontend (Vite :5173) with a single command:

### Windows (Batch — Double Click)
Double-click [`start.bat`](file:///d:/internship/VidhanAi-main/start.bat) in the project root.

### Windows (PowerShell — Recommended)
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\start.ps1
```

### Manual Launch
```bash
# Backend (Terminal 1)
cd backend
python app.py

# Frontend (Terminal 2)
cd frontend_new
npm run dev
```

Open your browser at: **`http://localhost:5173`**

---

## 📁 Repository Structure

```
VidhanAi/
├── start.bat                   # One-click Windows batch launcher
├── start.ps1                   # One-click PowerShell launcher with browser auto-open
├── render.yaml                 # Render.com Blueprint deployment (free tier)
├── vercel.json                 # Vercel deployment configuration
├── backend/                    # Flask REST API + Services
│   ├── app.py                  # Application factory
│   ├── routes.py               # API endpoints (diff, research, architecture, news)
│   ├── models.py               # 11-table SQLAlchemy database schema
│   ├── db_service.py           # SQLite operations
│   ├── ai_service.py           # QLoRA / Groq model selection & guardrails
│   ├── agents/
│   │   └── orchestrator.py     # CrewAI Multi-Agent stack & 7 tools
│   ├── services/
│   │   └── amendment_service.py# Pure-Python structural diffing engine
│   └── requirements.txt
├── frontend_new/               # React 19 + Vite 8 Frontend
│   ├── src/
│   │   ├── pages/              # Landing, Explore, Research, Amendments, Alerts, Architecture, Playground, Search
│   │   ├── components/         # Vid, BillCard, Sidebar, AdvancedFilters, BillPicker
│   │   └── services/api.js     # Axios API client
│   └── index.html
├── notebooks/                  # Training notebooks
│   └── qlora_finetuning.ipynb  # Kaggle QLoRA Llama-3.2-3B training script
└── docs/                       # Architectural documentation
    ├── ARCHITECTURE.md         # Full Mermaid diagrams & service inventory
    ├── MODEL_COMPARISON.md     # QLoRA vs zero-shot benchmark analysis
    └── PROJECT_TECH_STACK.md
```

---

## 🔌 API Endpoints Summary

| Service | Method | Endpoint | Description |
|---|---|---|---|
| **Health** | GET | `/api/health` | Service health status |
| **Search** | GET | `/api/semantic-search?query=tax` | ChromaDB vector search |
| **Bills** | GET | `/api/bills/<id>` | Full bill details + sentiment + timeline |
| **Summary** | GET | `/api/bills/<id>/summary` | QLoRA / Groq summary |
| **Amendment** | POST | `/api/amendment/diff` | Structural diff + LLM change narrative |
| **Versions** | GET | `/api/bills/<id>/versions` | Bill snapshot version history |
| **Research** | POST | `/api/agent/research` | CrewAI multi-agent reasoning trace |
| **News** | GET | `/api/bills/<id>/news` | CitationFinder Google News RSS |
| **Architecture** | GET | `/api/architecture` | Live service inventory JSON |

---

## 🚀 Free Deployment Guide

### Backend → Render.com (Free Tier)
1. Connect repository to [Render.com](https://render.com).
2. Create a new Web Service using [`render.yaml`](file:///d:/internship/VidhanAi-main/render.yaml).
3. Set environment variable `GROQ_API_KEY` in the Render dashboard.

### Frontend → Vercel.com (Free Tier)
1. Connect repository to [Vercel.com](https://vercel.com).
2. Root directory: `frontend_new` (uses the root [`vercel.json`](file:///d:/internship/VidhanAi-main/vercel.json)).
3. All `/api/*` routes are automatically rewritten to your Render backend host.

**Total monthly cost: $0.00**

---

## 📜 Rubric & Academic Alignment

| Course / Rubric Expectation | Implementation in VidhanAI |
|---|---|
| **Problem Domain Understanding** | Legislative simplification for Indian Parliament (PRS India data) |
| **Multi-Model Pipeline** | Local QLoRA Llama-3.2-3B → Groq `groq/compound` → Extractive fallback |
| **Service-Oriented Architecture** | Clean 6-service architecture (`backend/agents/`, `backend/services/`) |
| **Orchestration Layer** | CrewAI orchestrator with deterministic & LLM planner options |
| **IDE-like Interface** | Live Architecture visualizer page at `/architecture` |
| **Research Novelty** | Delta-aware amendment summarization (`amendment_service.py` + `/amendments`) |

---

## 📝 License & Citation

Licensed under the MIT License. Data sourced from **PRS Legislative Research** (https://prsindia.org).
