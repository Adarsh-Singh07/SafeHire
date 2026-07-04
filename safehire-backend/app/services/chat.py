import re
from typing import Optional, List, Dict, Any
from datetime import datetime, date
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
1. Ground your answer in the provided Context. If context contains company facts (status, incorporation, address, directors, ratings), state them.
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

def extract_company_name_query(message: str) -> Optional[str]:
    """
    Cleans up conversational question prefixes/suffixes from the message
    to isolate potential company names for JIT search lookups.
    """
    cleaned = message.strip().rstrip("?").strip()
    
    # Ignore long multi-sentence query paragraphs
    if len(cleaned) > 80:
        return None
        
    prompts = [
        r"^(what about|tell me about|who is|do you know|details of|details about|info about|information about|check|is|verify)\s+",
        r"\s+(is a good company|legitimate|is safe|safe|good company|scam|fraud|registry|details)$"
    ]
    for prompt in prompts:
        cleaned = re.sub(prompt, "", cleaned, flags=re.IGNORECASE).strip()
        
    if 3 <= len(cleaned) <= 60:
        words = [w.strip().lower() for w in cleaned.split()]
        conversational_words = {
            "should", "pay", "money", "secure", "work", "apply", "do", "how", "why", 
            "where", "can", "want", "need", "salary", "fee", "deposit", "fake", "scam", 
            "real", "genuine", "job", "recruiter", "interview", "get", "charge", "training",
            "laptop", "kit", "id", "activation", "give", "cost", "safe", "danger", "caution",
            "guidelines", "rules", "scammed", "report", "help", "hello", "cybercrime", "cyber",
            "thank", "thanks", "morning", "evening", "what", "when", "incorporate", "incorporated",
            "who", "director", "directors", "address", "location"
        }
        if any(w in conversational_words for w in words):
            return None
        return cleaned
    return None

async def resolve_company_jit(company_name: str, db: AsyncSession) -> Optional[Company]:
    """
    Just-In-Time resolution: Searches local cache, and runs live
    registries and reputation crawlers if missed, caching results dynamically.
    """
    from app.core.normalization import normalize_company_name
    from app.services.ogd_mca import lookup_mca_registry
    from app.services.search_reviews import lookup_company_reputation, discover_company_domain
    from app.services.rdap_domain import lookup_domain_age
    from app.core.config import settings
    import uuid

    normalized_name = normalize_company_name(company_name)
    
    # 1. Check local cache first
    stmt = select(Company).where(
        (Company.normalized_name == normalized_name) |
        (Company.name.like(f"%{company_name}%"))
    )
    result = await db.execute(stmt)
    company = result.scalars().first()
    if company:
        return company
        
    # 2. Run live verification crawler pipeline
    try:
        ogd_key = settings.GOV_API_KEY or settings.OGD_API_KEY
        mca_result = await lookup_mca_registry(company_name, ogd_api_key=ogd_key)
        
        if mca_result.get("unverified"):
            return None
            
        real_name = mca_result.get("name")
        cin = mca_result.get("cin")

        # Check by CIN before insertion
        if cin:
            stmt = select(Company).where(Company.cin == cin)
            res = await db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return existing
            
        # Run JIT reputation and domain age queries
        domain = await discover_company_domain(real_name)
        domain_age_data = await lookup_domain_age(domain) if domain else {}
        rep_data = await lookup_company_reputation(real_name, domain)
        
        def parse_iso_date(date_str: Optional[str]) -> Optional[date]:
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return None
                
        inc_date = parse_iso_date(mca_result.get("incorporation_date"))
        fil_date = parse_iso_date(mca_result.get("last_filing_date"))
        dom_created = parse_iso_date(domain_age_data.get("created_at"))
        
        # Add to database cache
        new_cache = Company(
            id=str(uuid.uuid4()),
            name=real_name,
            normalized_name=normalized_name,
            cin=cin,
            registration_status=mca_result.get("registration_status"),
            incorporation_date=inc_date,
            registered_address=mca_result.get("registered_address"),
            directors=mca_result.get("directors"),
            last_filing_date=fil_date,
            domain=domain,
            domain_created_at=dom_created,
            glassdoor_rating=rep_data.get("glassdoor_rating"),
            glassdoor_review_count=rep_data.get("glassdoor_review_count"),
            trustpilot_rating=rep_data.get("trustpilot_rating"),
            google_search_footprint=rep_data.get("google_search_footprint"),
            last_refreshed_at=datetime.utcnow()
        )
        db.add(new_cache)
        try:
            await db.flush()  # Detect constraint errors before committing
            await db.commit()
            await db.refresh(new_cache)
            return new_cache
        except Exception as conflict_err:
            # Rollback the broken transaction so the session stays healthy
            await db.rollback()
            # Race condition: another request already inserted this company.
            # Re-fetch the existing record and return it.
            try:
                if cin:
                    recover_stmt = select(Company).where(Company.cin == cin)
                    recover_res = await db.execute(recover_stmt)
                    existing = recover_res.scalars().first()
                    if existing:
                        return existing
                recover_stmt2 = select(Company).where(Company.normalized_name == normalized_name)
                recover_res2 = await db.execute(recover_stmt2)
                existing2 = recover_res2.scalars().first()
                if existing2:
                    return existing2
            except Exception:
                pass
            print(f"OfferShield JIT Cache Conflict (non-critical): {str(conflict_err)}")
            # Return the unsaved object — caller still gets the live data
            return new_cache
    except Exception as e:
        print(f"OfferShield Chat JIT Resolution Error: {str(e)}")
        try:
            await db.rollback()
        except Exception:
            pass

    return None

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

    # 2. RAG Step: JIT Company Verification lookup if mentioned in chat
    if db and not context_blocks:
        # Step 2A: Check if any token in the query message matches a cached company (Fast local RAG match)
        words = [w.strip() for w in message.split() if len(w) > 3]
        company = None
        for word in words:
            clean_word = "".join(c for c in word if c.isalnum()).lower()
            if clean_word in ["scam", "fraud", "job", "post", "offer", "letter", "glassdoor", "trustpilot", "rating", "reviews"]:
                continue
            if clean_word.endswith("s") and len(clean_word) > 3:
                clean_word = clean_word[:-1]
                
            stmt = select(Company).where(Company.normalized_name.like(f"%{clean_word}%"))
            res = await db.execute(stmt)
            company = res.scalars().first()
            if company:
                break
                
        # Step 2B: If not cached, extract company name and run JIT resolver
        if not company:
            extracted_name = extract_company_name_query(message)
            if extracted_name:
                company = await resolve_company_jit(extracted_name, db)
                
            if not company and extracted_name:
                company_context = (
                    f"WARNING: The company '{extracted_name}' could not be verified. "
                    f"A live lookup in the Registrar of Companies (RoC) registers and public search indexes returned NO matching records."
                )
                context_blocks.append(company_context)
                sources.append("RoC Government Records")
                
        # Step 2C: Feed resolved company info to prompt context block
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
            sources.append("Glassdoor")
            sources.append("Trustpilot")

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
        return ChatMessageResponse(
            reply=f"I'm sorry, I encountered an issue processing your request: {str(e)}. Please try again later.",
            grounded=False,
            sources=["Error Handling"]
        )
