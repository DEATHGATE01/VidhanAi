# 🏗️ VidhanAI Architecture Specification

> **Service-Oriented Architecture (SOA) & Multi-Agent System Specification**

This document provides a comprehensive technical overview of VidhanAI's microservice design, agent orchestration graph, vector search pipeline, and database schema.

---

## 1. System Context & Microservices Diagram

VidhanAI follows a strict **Service-Oriented Architecture (SOA)** where Flask acts as an API Gateway forwarding user requests to independent, decoupled service components.

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Layer"]
        UI["React 18 SPA (Vite)\nPorts: 3000 (Dev) / Vercel"]
    end

    subgraph GatewayLayer ["API Gateway Layer"]
        Flask["Flask REST API Gateway (app.py / routes.py)\nPort: 5000 / Render"]
    end

    subgraph ServiceLayer ["Service Layer"]
        AppSvc["Application Service\n(Routing & Auth)"]
        OrchSvc["Orchestration Layer\n(CrewAI Researcher)"]
        RAGSvc["RAG / Retrieval Service\n(ChromaDB Semantic Search)"]
        LLMSvc["LLM Service\n(QLoRA Llama-3.2-3B / Groq)"]
        DataSvc["Data / Knowledge Service\n(SQLite + PRS Scraper)"]
        GuardSvc["Guardrail Service\n(Input Safety & Output FactChecker)"]
        DiffSvc["AmendmentDiff Service\n(Structural & Factual Section Diff)"]
        NewsSvc["CitationFinder Service\n(Google News RSS)"]
    end

    subgraph StorageLayer ["Storage Layer"]
        SQLite[("SQLite DB\nregulation_alert.db\n(11 Tables)")]
        VectorDB[("ChromaDB\nlegal_bills Collection\n(all-MiniLM-L6-v2)")]
        LoRAModel[("LoRA Adapter\nnotebooks/lora_model/\n(97 MB Safetensors)")]
    end

    UI -->|HTTP / REST| Flask
    Flask --> AppSvc
    AppSvc --> OrchSvc
    OrchSvc --> GuardSvc
    OrchSvc --> DataSvc
    OrchSvc --> RAGSvc
    OrchSvc --> LLMSvc
    OrchSvc --> DiffSvc
    OrchSvc --> NewsSvc

    DataSvc --> SQLite
    RAGSvc --> VectorDB
    LLMSvc --> LoRAModel
    LLMSvc -.->|Cloud Fallback| GroqAPI["Groq Cloud API\n(groq/compound)"]
```

---

## 2. Multi-Agent Orchestration Sequence

When a user submits a question on the `/research` page, the request executes through the following CrewAI agent orchestration flow:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as React Frontend
    participant Gateway as Flask Gateway (/api/agent/research)
    participant Agent as CrewAI Researcher Agent
    participant Guard as Guardrail Tool
    participant Data as DataService (bill_lookup)
    participant RAG as RAGService (semantic_search)
    participant LLM as LLMService (summarize_bill)
    participant Fact as FactChecker (fact_check)

    User->>Frontend: Submit Question ("What is the Telecom Bill 2023 about?")
    Frontend->>Gateway: POST /api/agent/research
    Gateway->>Agent: Kickoff Research Execution

    Agent->>Guard: check_input_safe(question)
    Guard-->>Agent: "safe"

    Agent->>Data: bill_lookup("Telecom Bill 2023")
    Data-->>Agent: JSON Bill Metadata (ID, Title, Ministry, URL)

    Agent->>RAG: semantic_search("Telecom Bill 2023 passage", n=3)
    RAG-->>Agent: JSON Relevant Excerpts

    Agent->>LLM: summarize_bill(excerpt, max_words=250)
    LLM-->>Agent: Plain-English Summary

    Agent->>Fact: fact_check(summary, original_text)
    Fact-->>Agent: {"hallucination_risk": "low", "claims_found": [...]}

    Agent->>Gateway: Synthesized Grounded Response + Traces
    Gateway->>Frontend: 200 OK (Answer + Agent Trace JSON)
    Frontend->>User: Render Chat Bubble & Staggered Agent Trace Cards
```

---

## 3. Delta-Aware Amendment Diff Architecture

The **AmendmentDiff Service** (`services/amendment_service.py`) implements structural section diffing between two bill versions without invoking an LLM for the diff computation itself (keeping execution deterministic and cost at $0):

```mermaid
flowchart LR
    subgraph Input ["Input Bills"]
        V1["Bill Text v1 (Older)"]
        V2["Bill Text v2 (Newer)"]
    end

    subgraph Engine ["amendment_service.py Engine"]
        Splitter["Header Parser & Section Splitter"]
        Jaccard["Jaccard Shingle Similarity Matrix"]
        RegexFacts["Regex Fact Extractor\n(Rs/₹, Dates, Years, Penalties)"]
    end

    subgraph Output ["Structural Output"]
        Added["Added Sections (+ GREEN)"]
        Removed["Removed Sections (- RED)"]
        Modified["Modified Sections (~ AMBER)"]
        Facts["Changed Facts List"]
    end

    subgraph LLMNarrative ["LLM Layer"]
        Groq["ai_service.generate_change_narrative()"]
    end

    V1 --> Splitter
    V2 --> Splitter
    Splitter --> Jaccard
    Splitter --> RegexFacts
    Jaccard --> Added
    Jaccard --> Removed
    Jaccard --> Modified
    RegexFacts --> Facts
    Added & Removed & Modified & Facts --> Groq
    Groq --> SummaryNarrative["Final Change Narrative"]
```

---

## 4. Database Schema (SQLite 11-Table ER Diagram)

```mermaid
erDiagram
    BILLS ||--o| BILL_CONTENTS : has
    BILLS ||--o| BILL_SUMMARIES : has
    BILLS ||--o{ BILL_VERSIONS : tracks
    USERS ||--o{ USER_FAVORITES : saves
    USERS ||--o{ USER_READING_HISTORY : reads
    USERS ||--o{ SEARCH_HISTORY : performs
    USER_SUBSCRIPTIONS ||--o{ BILL_NOTIFICATIONS : triggers
    BILLS ||--o{ BILL_NOTIFICATIONS : notifies

    BILLS {
        int id PK
        string bill_id UK
        string title
        string ministry
        string status
        string url
        datetime introduction_date
    }

    BILL_CONTENTS {
        int id PK
        int bill_id FK
        text full_text
        json sections
        json paragraphs
        string pdf_link
    }

    BILL_SUMMARIES {
        int id PK
        int bill_id FK
        text summary
        string summary_type
        float confidence
        string model_version
        float sentiment_score
    }

    BILL_VERSIONS {
        int id PK
        int bill_id FK
        int version_number
        datetime version_date
        string change_type
        text full_text
        text changes_summary
    }

    USER_SUBSCRIPTIONS {
        int id PK
        string email
        json keywords
        json ministries
        boolean is_active
    }
```

---

## 5. Live Architecture Endpoint (`/api/architecture`)

The `/api/architecture` endpoint generates a live JSON inventory of all registered services, tools, data stores, and model backends. This fulfills the **IDE-like interface** criteria by letting reviewers inspect system capabilities directly through the frontend at `/architecture`.
