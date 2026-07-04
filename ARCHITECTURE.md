# OfferShield — System Architecture

This document describes the high-level architecture, module integrations, and database schemas for the **OfferShield** platform.

---

## 1. Tech Stack (Phase 1 MVP)

*   **Backend**: FastAPI (Python 3.10+) — Handles API routing, lifespan hooks, and services.
*   **Database**: SQLite via the asynchronous `aiosqlite` DBAPI driver, managed by SQLAlchemy 2.0 ORM.
*   **ORM**: SQLAlchemy 2.0 (using type-annotated `Mapped` structures and `selectin` eager loading for async relationships).
*   **AI/NLP**: LangChain wrappers for ChatGroq (Llama 3) and ChatGoogleGenerativeAI (Gemini 1.5 Flash).
*   **Vector Embeddings**: Local ChromaDB instance to store and query vectorized text documents for the RAG chatbot.
*   **Testing**: Pytest for HTTP/API route testing and a custom async runner (`tests/run_db_tests.py`) for in-memory SQLite schema tests.

---

## 2. Core Modules

1.  **Ingestion & Data Pipelines**: Interfaces with the `data.gov.in` OGD endpoint to verify active registration status, address, directors, and filing dates for Indian firms.
2.  **Scoring & Verification Engine**: Calculates a deterministic, explainable safety score (0–100) using weights across text patterns, domain age, and review rankings.
3.  **Fuzzy Company Matching**: Suffix-stripped name normalizer matching queries against registry records using edit distance thresholds (80%–85%).
4.  **AI Chatbot Assistant**: Grounded RAG-based chatbot responding to user inquiries about job safety, referencing logged results.

---

## 3. Database Schema

The database relies on four primary tables:
*   `users`: Tracks registered job seeker accounts and basic authentication credentials.
*   `companies`: Caches public registry data retrieved from the OGD platform to avoid hitting API rate limits.
*   `job_checks`: Logs job details submitted by users, containing composite safety score metrics and risk bands.
*   `safety_logs`: Captures the inputs and weights used in scoring calculations, ensuring complete transparency.
