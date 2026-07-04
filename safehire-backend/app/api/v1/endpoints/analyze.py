import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import JobAnalysisRequest, TrustScoreResponse
from app.services.scraper import scrape_job_url, ScraperError
from app.services.domain_agent import analyze_domain
from app.services.llm_analysis import analyze_job_text
from app.core.scoring import calculate_final_score
from app.services.vector_db import query_scam_vectors

router = APIRouter()

@router.post("/", response_model=TrustScoreResponse)
async def analyze_job(request: JobAnalysisRequest):
    raw_text = ""
    domain_data = {"is_new": False, "unverified": True, "error": "No URL provided"}
    
    if request.url:
        url_str = str(request.url)
        try:
            if request.raw_text:
                # If the extension already provided the DOM text, skip the scraper!
                raw_text = request.raw_text
                domain_result = await analyze_domain(url_str)
            else:
                # Run scraper and domain analysis concurrently
                scrape_result, domain_result = await asyncio.gather(
                    scrape_job_url(url_str),
                    analyze_domain(url_str),
                    return_exceptions=True
                )
                
                if isinstance(scrape_result, Exception):
                    raise scrape_result
                    
                raw_text = scrape_result.raw_description
                
            if not isinstance(domain_result, Exception):
                domain_data = domain_result
            else:
                domain_data = {"is_new": False, "unverified": True, "error": str(domain_result)}
                
        except ScraperError as e:
            raise HTTPException(status_code=400, detail=str(e))
    elif request.raw_text:
        raw_text = request.raw_text
        
    if not raw_text:
        raise HTTPException(status_code=400, detail="Could not extract text from the provided URL, and no raw_text was provided.")
        
    # Send text to LLM and Vector DB concurrently
    llm_result, vector_result = await asyncio.gather(
        analyze_job_text(raw_text),
        query_scam_vectors(raw_text),
        return_exceptions=True
    )
    
    if isinstance(llm_result, Exception):
        llm_result = {"semantic_score": 50, "scam_indicators_found": [f"Error during LLM analysis: {str(llm_result)}"], "justification": "LLM Analysis failed."}
    
    if isinstance(vector_result, Exception):
        vector_result = {"matches": [], "high_confidence_match": False, "error": str(vector_result)}
        
    # Calculate final score
    scoring_result = calculate_final_score(llm_result.get("semantic_score", 50), domain_data, vector_result)
    
    # Compile red flags
    all_red_flags = llm_result.get("scam_indicators_found", []) + scoring_result.get("domain_red_flags", [])
    
    return TrustScoreResponse(
        trust_score=scoring_result["trust_score"],
        risk_level=scoring_result["risk_level"],
        summary=llm_result.get("justification", "Analysis completed."),
        red_flags=all_red_flags
    )
