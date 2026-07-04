from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.schemas import JobAnalysisRequest, SafetyScoreResponse, CompanyLookupResponse, JobScanResult
from app.models.job_check import JobCheck
from app.models.safety_log import SafetyLog
from app.services.scanner import scan_job_posting_text
from app.services.ogd_mca import lookup_mca_registry
from app.services.search_reviews import lookup_company_reputation, discover_company_domain
from app.services.rdap_domain import lookup_domain_age
from app.services.url_scraper import scrape_job_description
from app.core.scoring import calculate_composite_safety_score
from app.core.config import settings

router = APIRouter()

@router.post("/job", response_model=SafetyScoreResponse)
async def scan_job(
    request: JobAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    text_to_scan = request.raw_text
    url_str = str(request.url) if request.url else None
    
    # Live URL Scraping (Combined Phase 2 crawler)
    if not text_to_scan and url_str:
        try:
            print(f"OfferShield Crawler: Scraping job listing from URL: {url_str}...")
            text_to_scan = await scrape_job_description(url_str)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to scrape the provided job URL: {str(e)}"
            )
        
    if not text_to_scan:
        raise HTTPException(
            status_code=400, 
            detail="Either raw_text or url must be provided for job scanning."
        )
        
    try:
        # 1. Company Registry & Reputation Checks
        mca_result = {}
        if request.company_name:
            ogd_key = settings.GOV_API_KEY or settings.OGD_API_KEY
            mca_result = await lookup_mca_registry(request.company_name, ogd_api_key=ogd_key)
            
            # Run Phase 2 reputation crawlers only if company has matched a record
            if not mca_result.get("unverified"):
                company_name = mca_result.get("name")
                
                # Discover official website domain
                domain = mca_result.get("domain") or await discover_company_domain(company_name)
                
                # Determine domain for WHOIS/RDAP verification
                # Check email domain first if provided, else company website domain
                whois_domain = None
                if request.recruiter_email:
                    whois_domain = request.recruiter_email.split("@")[-1]
                else:
                    whois_domain = domain
                    
                domain_age_data = await lookup_domain_age(whois_domain) if whois_domain else {}
                rep_data = await lookup_company_reputation(company_name, domain)
                
                # Merge indicators into registry dictionary for composite scoring
                mca_result.update({
                    "domain": domain,
                    "domain_created_at": domain_age_data.get("created_at"),
                    "domain_age_months": domain_age_data.get("age_months"),
                    "domain_unverified": domain_age_data.get("unverified"),
                    "domain_error": domain_age_data.get("error"),
                    "glassdoor_rating": rep_data.get("glassdoor_rating"),
                    "glassdoor_review_count": rep_data.get("glassdoor_review_count"),
                    "trustpilot_rating": rep_data.get("trustpilot_rating"),
                    "google_search_footprint": rep_data.get("google_search_footprint")
                })
        else:
            mca_result = {
                "unverified": True,
                "error": "No company name provided for registry check.",
                "source": "none",
                "match_score": 0.0
            }
            
        company_lookup_resp = CompanyLookupResponse(**mca_result)
        
        # 2. Text Scam Scanner Check (Module 3)
        scan_result = await scan_job_posting_text(text_to_scan)
        
        # 3. Composite Safety Score Calculation (Module 4)
        score_data = calculate_composite_safety_score(
            company_registry=mca_result,
            job_scan=scan_result.model_dump(),
            recruiter_email=request.recruiter_email
        )
        
        # 4. Save JobCheck record to the SQLite database
        new_check = JobCheck(
            url=url_str,
            title=request.company_name or "Unknown Job",
            company_name=request.company_name,
            raw_text=text_to_scan,
            composite_score=score_data["trust_score"],
            risk_level=score_data["risk_level"],
            details={
                "company_verification": mca_result,
                "job_scan": scan_result.model_dump(),
                "explanations": score_data["explanations"]
            }
        )
        db.add(new_check)
        await db.flush()  # Populate new_check.id
        
        # 5. Save SafetyLog audit trail record (FR-5.4)
        new_log = SafetyLog(
            job_check_id=new_check.id,
            inputs=score_data["inputs"],
            weights=score_data["deductions"],
            resulting_score=score_data["trust_score"]
        )
        db.add(new_log)
        await db.commit()
        
        return SafetyScoreResponse(
            job_check_id=new_check.id,
            trust_score=score_data["trust_score"],
            risk_level=score_data["risk_level"],
            company_verification=company_lookup_resp,
            job_scan=scan_result,
            explanations=score_data["explanations"]
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Scoring pipeline transaction failed: {str(e)}"
        )
