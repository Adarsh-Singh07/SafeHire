# Changelog

All notable changes to the **OfferShield** platform will be documented in this file.

---

## [Unreleased] — 2026-07-04

### Added
*   Defined Phase 1 relational database schemas and SQLAlchemy 2.0 async models (`User`, `Company`, `JobCheck`, and `SafetyLog`) in `app/models/`.
*   Configured async SQLAlchemy engine and Session Local engine dependencies in `app/db/session.py`.
*   Integrated database table schema migrations into the FastAPI lifespan startup routine in `app/main.py`.
*   Built a standalone asynchronous database testing suite (`tests/run_db_tests.py`) validating model creation and relationship lazy-loading.
*   Updated API health and basic check endpoints to reflect dynamic scoring ranges rather than hardcoded scores in `test_api.py`.
*   Created `ARCHITECTURE.md` documenting tech stack details and core design constraints.
*   Implemented Company Identity Verification service (`app/services/ogd_mca.py`) supporting the `data.gov.in` OGD REST portal with a local seed fallback.
*   Wrote company name suffix-stripping normalization and fuzzy matching ratios (80%–85% thresholds) using `difflib` in `app/core/normalization.py`.
*   Built company search and query-by-CIN endpoints in `app/api/v1/endpoints/company.py` with automatic 30-day SQLite caching.
*   Created comprehensive unit tests in `tests/run_company_tests.py` verifying query matching, caching validation, and unregistered entity fallback.
*   Implemented unified structured LLM client `invoke_fallback_chain` in `app/services/llm.py` with a multi-model fallback chain for Groq (Llama 3.3/3.1) and Google Gemini (Gemini 2.0/1.5).
*   Created Job Posting Risk Scanner service in `app/services/scanner.py` leveraging structured extraction to flag scam patterns.
*   Added POST `/api/v1/scan/job` endpoint in `app/api/v1/endpoints/scan.py` and registered it in `app/main.py`.
*   Appended `RiskIndicator` and `JobScanResult` Pydantic schemas to `app/models/schemas.py`.
*   Created unit tests in `tests/run_scan_tests.py` verifying detection of legitimate listings vs. deposit/urgency scams.
*   Implemented deterministic safety scoring algorithm in `app/core/scoring.py` assessing registry status, firm age, LLM content risks, and email domains, mapped into Low/Medium/High risk bands.
*   Modified `/api/v1/scan/job` to run company searches, text scans, and score calculations sequentially.
*   Exposed `GET /api/v1/score/{check_id}` in `app/api/v1/endpoints/score.py` to retrieve audit log calculations.
*   Added `SafetyScoreResponse` to `app/models/schemas.py` to validate unified scoring results.
*   Created unit tests in `tests/run_score_tests.py` verifying end-to-end score transactions, database inserts, and retrieve paths.
*   Implemented RAG Chatbot service in `app/services/chat.py` grounding replies in either safety guidelines, database registry cache records, or scoring audit records.
*   Added POST `/api/v1/chat/message` chatbot endpoint in `app/api/v1/endpoints/chat.py` and registered it in `app/main.py`.
*   Appended `ChatMessageRequest` and `ChatMessageResponse` Pydantic schemas to `app/models/schemas.py`.
*   Created comprehensive unit tests in `tests/run_chat_tests.py` verifying guidelines advice, company record RAG checks, and safety score audit trace grounding.
*   Implemented live OGD Government MCA API datastore search utilizing dataset resource ID `4dbe5667-7b6b-41d7-82af-211562424d9a`.
*   Implemented Google search crawler using Serper.dev to extract aggregate company ratings and reviews count from Glassdoor and Trustpilot.
*   Implemented domain-discovery crawler finding company websites automatically based on search patterns.
*   Implemented WHOIS domain registration age verification using modern standard Registration Data Access Protocol (RDAP).
*   Implemented live URL job posting scraper parsing description text using `httpx` and `BeautifulSoup4`.
*   Modified SQLite database schema adding columns caching website domains, WHOIS creation dates, Glassdoor/Trustpilot star ratings, and web footprints.
*   Enhanced composite scoring calculator adding deductions checking for newly registered domains (-25 points), unresolved domains (-35 points), low footprints (-20 points), and low Glassdoor/Trustpilot scores (-15 points).
*   Updated glassmorphic web SPA dashboard displaying reputation metrics, domains, and ratings side-by-side with registry details.
*   Created new automated verification script in `tests/run_live_integration_tests.py` testing live connections.
*   Created premium Apple-like Glassmorphic Single Page Application (SPA) dashboard in `app/static/index.html`.
*   Defined modern translucent tokens, glow gradients, floating background lights, responsive grid structure, and animated SVG score visualizers in `app/static/style.css`.
*   Implemented frontend logic in `app/static/app.js` managing scan submissions, fuzzy registry queries, JIT consent validation, and markdown chat replies.
*   Mounted `StaticFiles` and registered `/` root routing to index.html in `app/main.py`.
*   Added unit tests in `test_api.py` verifying HTML/SPA delivery at root path.
