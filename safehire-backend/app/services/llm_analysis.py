from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.core.config import settings

class LLMAnalysisResult(BaseModel):
    semantic_score: int = Field(description="Score from 0 to 100 where 100 means perfectly safe and 0 means certain scam.")
    scam_indicators_found: List[str] = Field(description="List of specific scam indicators found in the text.")
    justification: str = Field(description="Detailed explanation of the semantic score.")

async def analyze_job_text(text: str) -> Dict[str, Any]:
    """
    Handles the AI reasoning using langchain and groq.
    """
    try:
        # Check if API key is configured
        if not settings.GROQ_API_KEY:
            return {
                "semantic_score": 75,
                "scam_indicators_found": ["API Key not configured. Using fallback semantic analysis."],
                "justification": "Could not perform LLM analysis due to missing GROQ API key."
            }

        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.GROQ_API_KEY)
        structured_llm = llm.with_structured_output(LLMAnalysisResult)
        
        prompt_template = PromptTemplate.from_template(
            """You are a STRICT job scam detection AI with expertise in Indian job market fraud patterns. 
            Your job is to critically analyse a job posting and assign a trust score.
            Be skeptical. Do NOT give high scores unless the job is clearly from a legitimate, established company.

            CRITICAL RED FLAGS to look for (any ONE of these should heavily penalize the score):
            1. Unrealistic salary/earnings (e.g. "Earn ₹50,000/day", "weekly payout", "₹500-₹1000 per hour for simple tasks")
            2. Any fee, deposit, or investment required from the candidate
            3. Asking candidate to buy their own equipment/materials upfront
            4. "Work from home" combined with vague/no company name
            5. Data entry, form filling, typing, copy-paste, ad-clicking jobs
            6. Communication moved to WhatsApp, Telegram, or personal email
            7. Guaranteed income or "no experience needed" for high-paying roles
            8. Multi-level marketing or "refer friends to earn"
            9. Overly vague job description with no specific skills required
            10. Request for personal documents or bank details upfront
            11. Poor grammar, spelling errors, or unprofessional language
            12. No company name, address, or registration number mentioned
            13. "Part-time" + "high pay" + "easy work" combination
            14. Promises of government job or visa sponsorship for a fee
            
            SCORING GUIDE:
            - 90-100: Established company, clear role, verifiable company name, professional description
            - 70-89: Mostly legitimate but minor concerns (e.g., very vague description)
            - 50-69: Several yellow flags, proceed with caution
            - 20-49: Multiple red flags, likely a scam
            - 0-19: Certain scam pattern detected

            Job Posting Text:
            {text}
            
            Be critical. A score of 98 should be rare. Most real jobs should score 75-90.
            """
        )
        
        prompt = prompt_template.format(text=text)
        result = await structured_llm.ainvoke(prompt)
        
        return result.model_dump()
        
    except Exception as e:
        return {
            "semantic_score": 50,
            "scam_indicators_found": [f"Error during LLM analysis: {str(e)}"],
            "justification": "LLM Analysis failed."
        }
