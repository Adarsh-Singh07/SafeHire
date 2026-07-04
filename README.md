# SafeHire AI (OfferShield)

SafeHire is a premium, AI-powered security verification platform designed to protect job seekers from employment scams, fake listings, and fraudulent organizations. The platform combines official government registries, real-time web crawler footprints, WHOIS domain data, and multi-model LLM verification to calculate a deterministic, explainable safety score (0–100) for any job posting.

It comes equipped with a FastAPI backend serving a gorgeous **Glassmorphic Single Page Application (SPA)** and a **Chrome Extension** that allows users to scan job postings directly from their browser.

---

## Key Features

1. **Deterministic Safety Scoring**: Calculates safety metrics and maps them into clear risk bands (Low, Medium, High) based on company age, registration status, user reviews, domain registration details, and content analysis.
2. **Official MCA Integration**: Interacts with the `data.gov.in` OGD REST portal using fuzzy name matching to verify active Indian corporate registrations.
3. **Multi-Model LLM Fallback Chain**: Utilizes zero-cost models across Groq (Llama 3.3/3.1) and Google Gemini (Gemini 2.0/1.5) sequentially to parse job descriptions for urgency, deposit demands, or phishing attempts.
4. **Active Footprint Analysis**: Verifies company web presence, reviews, and domain age using WHOIS RDAP and Google Serper reviews API.
5. **RAG Chatbot Assistant**: An interactive AI chat grounded in local database records, registry caches, and safety score audit trails to answer queries about specific offers.
6. **Chrome Browser Extension**: A companion extension that captures job description data straight from active tabs and sends them directly to the local backend.

---

## Repository Structure

```text
SafeHire/
├── safehire-backend/     # FastAPI backend service
│   ├── app/              # Source code (API endpoints, DB models, AI logic)
│   ├── tests/            # Automated unit testing suite
│   ├── requirements.txt  # Python package dependencies
│   └── .env.example      # Example environment configuration file
├── extension/            # Chrome Extension directory
│   ├── manifest.json     # Chrome Extension manifest
│   ├── background.js     # Service worker processing scans
│   ├── content.js        # Script to inject into job listing pages
│   └── popup.html/.js    # Extension UI and history list
├── ARCHITECTURE.md       # High-level architecture documentation
├── CHANGELOG.md          # Comprehensive history of project changes
└── README.md             # This file
```

---

## Getting Started

### 1. Backend Setup

Prerequisites: Python 3.10+ installed.

1. Navigate to the backend directory:
   ```bash
   cd safehire-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure your environment variables:
   * Copy the `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   * Open `.env` and fill in the required API keys (e.g., Groq, Gemini, Serper.dev, OGD Govt API key).

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```

7. Open your browser and navigate to `http://localhost:8000` to view the Glassmorphic SPA Dashboard. API documentation is available at `http://localhost:8000/docs`.

---

## 2. Chrome Extension Setup

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle switch in the top-right corner.
3. Click on the **Load unpacked** button in the top-left corner.
4. Select the `extension` folder from the root of this project.
5. The SafeHire extension icon will now appear in your browser toolbar, ready to scan active job postings and communicate with your running backend API.

---

## Development & Testing

Run the automated backend test suite to verify database operations, API endpoints, scanning, and chat RAG functionality:

```bash
cd safehire-backend
pytest
```
