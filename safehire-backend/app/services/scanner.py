from typing import Dict, Any
from app.services.llm import invoke_fallback_chain
from app.models.schemas import JobScanResult

SCANNER_PROMPT_TEMPLATE = """You are a strict, expert job fraud detection assistant for the Indian job market (OfferShield).
Analyze the following job posting text carefully for security risk indicators.

Verify against these standard scam indicators:
1. Upfront Payments: Asking candidate to pay a security deposit, registration fee, document fee, or purchase training/kits.
2. Unrealistic Salary: Offering exceptionally high pay for simple roles (e.g., "Earn ₹40,000/week copy-pasting data").
3. Vague Roles: Very low detail about specific duties, saying things like "just work from home on mobile".
4. Urgent/Pressure Language: Creating fake urgency ("Apply immediately", "Spot selection today").
5. Requesting Sensitive PII: Asking for Aadhaar, PAN, or bank credentials before any interview.
6. Communication channel: Asking to chat only via WhatsApp or Telegram.
7. Poor grammar/structure: Significant spelling mistakes or unprofessional wording.

Job Posting Text:
{text}

Instructions:
- Be skeptical. If there are signs of fraud, set is_scam to True.
- Assign a sub_score_impact (from 0 to 40) for each detected indicator based on its severity (e.g., upfront payment is 40 points, poor grammar is 5-10 points).
- Detect if the language is English or Hindi.
"""

async def scan_job_posting_text(text: str) -> JobScanResult:
    """
    Scans a job posting description for fraud risk indicators.
    Uses the multi-model LLM fallback chain.
    """
    if not text or not text.strip():
        return JobScanResult(
            is_scam=False,
            detected_indicators=[],
            justification="No text provided for scanning.",
            detected_language="English"
        )
        
    # Run the LLM structured fallback chain
    result = await invoke_fallback_chain(
        prompt_template=SCANNER_PROMPT_TEMPLATE,
        variables={"text": text},
        response_model=JobScanResult
    )
    return result
