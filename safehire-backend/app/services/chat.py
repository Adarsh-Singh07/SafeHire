from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_check import JobCheck
from app.models.company import Company
from app.models.schemas import ChatMessageResponse
from app.services.llm import invoke_fallback_chain
from pydantic import BaseModel, Field

# Internal structure for LLM output parsing
class ChatbotStructuredOutput(BaseModel):
    reply: str = Field(description="The conversational response to the user. Clear, polite, and directly addressing the question.")
    grounded: bool = Field(description="True if the reply strictly references verified context facts. False if it uses general advice.")
    sources: List[str] = Field(description="List of sources cited (e.g. 'RoC Government Records', 'Job Check Audit', etc.)")

CHAT_PROMPT_TEMPLATE = """You are "Shieldy", the friendly AI job-safety assistant for OfferShield.
Help job seekers identify scams and verify Indian companies.

CRITICAL RULES:
1. Ground your answer in the provided Context. If context contains company facts (status, incorporation, address, directors), state them.
2. Clearly distinguish between verified facts (e.g., "RoC records show X was incorporated in 2020") and general advice/opinion (e.g., "Be cautious when sharing details").
3. Do NOT make up/hallucinate any company registration dates, directors, or address details. If they are not in the context, say they are unverified.
4. Support both English and Hindi. Answer in the same language as the user query.
5. If the user indicates they have been scammed or lost money, advise them to file a cybercrime report (cybercrime.gov.in) and use the File Report option.

Context:
{context}

User Message:
{message}
"""

DEFAULT_CONTEXT = """
OfferShield General Safety Guidelines:
- Legitimate companies in India NEVER ask candidates to pay for training, laptop kits, ID activation, or security deposits. Any fee request is a high-risk scam.
- Avoid recruiters who communicate solely via personal WhatsApp or Telegram channels and refuse official email/video calls.
- Legitimate corporate emails match their official domain (e.g., info@wipro.com) instead of free hosts (e.g., wiprohr@gmail.com).
- Newly incorporated firms (under 6 months old) should be scrutinized closely for physical office addresses and active ROC registry.
"""

async def generate_chatbot_response(
    message: str,
    job_check_id: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> ChatMessageResponse:
    """
    Retrieves relevant company or job check context from the database (RAG) 
    and generates a grounded response using the LLM fallback chain.
    """
    context_blocks = []
    sources = []
    
    # 1. RAG Step: Retrieve Job Check Context by ID
    if job_check_id and db:
        stmt = select(JobCheck).where(JobCheck.id == job_check_id)
        result = await db.execute(stmt)
        job_check = result.scalars().first()
        if job_check:
            details = job_check.details or {}
            company_verify = details.get("company_verification", {})
            scan_result_dict = details.get("job_scan", {})
            explanations = details.get("explanations", [])
            
            check_context = (
                f"Job Check Audit #{job_check.id}:\n"
                f"- Job Title: {job_check.title}\n"
                f"- Company: {job_check.company_name}\n"
                f"- Final Trust Score: {job_check.composite_score}/100 ({job_check.risk_level} Risk)\n"
                f"- Detected Risks: {scan_result_dict.get('detected_indicators', [])}\n"
                f"- Score Deductions Justification: {explanations}\n"
                f"- Verified Company Registry: {company_verify}\n"
            )
            context_blocks.append(check_context)
            sources.append(f"Job Check Audit #{job_check.id}")

    # 2. RAG Step: Retrieve Company details by name matching if mentioned
    if db and not context_blocks:
        # Quick token-based company lookup
        words = [w.strip() for w in message.split() if len(w) > 3]
        for word in words:
            clean_word = "".join(c for c in word if c.isalnum()).lower()
            
            # Ignore search query keywords
            if clean_word in ["scam", "fraud", "job", "post", "offer", "letter", "glassdoor", "trustpilot", "rating", "reviews"]:
                continue
                
            # Strip trailing "s" for possessives (e.g. "Wipro's" -> "wipro")
            if clean_word.endswith("s") and len(clean_word) > 3:
                clean_word = clean_word[:-1]
                
            stmt = select(Company).where(Company.normalized_name.like(f"%{clean_word}%"))
            res = await db.execute(stmt)
            company = res.scalars().first()
            if company:
                company_context = (
                    f"Verified RoC Registry Record for '{company.name}':\n"
                    f"- CIN: {company.cin}\n"
                    f"- Status: {company.registration_status}\n"
                    f"- Incorporation Date: {company.incorporation_date}\n"
                    f"- Registered Address: {company.registered_address}\n"
                    f"- Directors: {company.directors}\n"
                    f"- Discovered Website: {company.domain or 'N/A'}\n"
                    f"- Glassdoor Rating: {company.glassdoor_rating or 'N/A'} stars ({company.glassdoor_review_count or 0} reviews)\n"
                    f"- Trustpilot Rating: {company.trustpilot_rating or 'N/A'} stars\n"
                    f"- Search Presence: {company.google_search_footprint or 'Low'}\n"
                )
                context_blocks.append(company_context)
                sources.append(f"RoC/MCA Government Records ({company.name})")
                break # Limit to 1 company context for prompt limits

    # 3. Fallback to default general safety context
    if not context_blocks:
        context_blocks.append(DEFAULT_CONTEXT)
        sources.append("OfferShield General Safety Guidelines")
        
    context = "\n\n".join(context_blocks)
    
    # 4. Generate structured response
    try:
        llm_output = await invoke_fallback_chain(
            prompt_template=CHAT_PROMPT_TEMPLATE,
            variables={"context": context, "message": message},
            response_model=ChatbotStructuredOutput
        )
        
        # Merge manual source tags and LLM-defined tags
        combined_sources = list(set(sources + llm_output.sources))
        
        return ChatMessageResponse(
            reply=llm_output.reply,
            grounded=llm_output.grounded,
            sources=combined_sources
        )
    except Exception as e:
        # Graceful fallback in case LLM completely fails
        return ChatMessageResponse(
            reply=f"I'm sorry, I encountered an issue processing your request: {str(e)}. Please try again later.",
            grounded=False,
            sources=["Error Handling"]
        )
