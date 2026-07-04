from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, date
from typing import Optional
from app.db.session import get_db
from app.models.company import Company
from app.models.schemas import CompanyLookupResponse
from app.services.ogd_mca import lookup_mca_registry
from app.services.search_reviews import lookup_company_reputation, discover_company_domain
from app.services.rdap_domain import lookup_domain_age
from app.core.config import settings

router = APIRouter()

@router.get("/search", response_model=CompanyLookupResponse)
async def search_company(
    query: str = Query(..., min_length=2, description="Company name or CIN"),
    db: AsyncSession = Depends(get_db)
):
    # 1. Normalize query
    from app.core.normalization import normalize_company_name
    normalized_query = normalize_company_name(query)
    
    # 2. Check if company is already cached in database
    stmt = select(Company).where(
        (Company.cin == query.strip().upper()) | 
        (Company.normalized_name == normalized_query)
    )
    result = await db.execute(stmt)
    cached_company = result.scalars().first()
    
    # 3. Verify cache expiration (fresh if < 30 days old)
    if cached_company:
        cache_age = datetime.utcnow() - cached_company.last_refreshed_at
        if cache_age < timedelta(days=30):
            inc_date = cached_company.incorporation_date.isoformat() if cached_company.incorporation_date else None
            filing_date = cached_company.last_filing_date.isoformat() if cached_company.last_filing_date else None
            dom_created = cached_company.domain_created_at.isoformat() if cached_company.domain_created_at else None
            
            return CompanyLookupResponse(
                name=cached_company.name,
                cin=cached_company.cin,
                registration_status=cached_company.registration_status,
                incorporation_date=inc_date,
                registered_address=cached_company.registered_address,
                directors=cached_company.directors,
                last_filing_date=filing_date,
                source="cache",
                match_score=1.0,
                domain=cached_company.domain,
                domain_created_at=dom_created,
                glassdoor_rating=cached_company.glassdoor_rating,
                glassdoor_review_count=cached_company.glassdoor_review_count,
                trustpilot_rating=cached_company.trustpilot_rating,
                google_search_footprint=cached_company.google_search_footprint
            )
            
    # 4. Cache stale or missing: Hit registry (data.gov.in / local fallback)
    ogd_key = settings.GOV_API_KEY or settings.OGD_API_KEY
    mca_result = await lookup_mca_registry(query, ogd_api_key=ogd_key)
    
    # Return unverified or suggestion immediately without caching
    if mca_result.get("unverified") or mca_result.get("source") == "local_suggestion":
        return CompanyLookupResponse(**mca_result)
        
    company_name = mca_result.get("name")
    
    # Run Phase 2 crawlers to discover domain and reputation details
    domain = await discover_company_domain(company_name)
    domain_age_data = await lookup_domain_age(domain) if domain else {}
    rep_data = await lookup_company_reputation(company_name, domain)
    
    # 5. Populate/update database cache for direct matches
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

    if cached_company:
        cached_company.name = company_name
        cached_company.normalized_name = normalized_query
        cached_company.registration_status = mca_result.get("registration_status")
        cached_company.incorporation_date = inc_date
        cached_company.registered_address = mca_result.get("registered_address")
        cached_company.directors = mca_result.get("directors")
        cached_company.last_filing_date = fil_date
        cached_company.domain = domain
        cached_company.domain_created_at = dom_created
        cached_company.glassdoor_rating = rep_data.get("glassdoor_rating")
        cached_company.glassdoor_review_count = rep_data.get("glassdoor_review_count")
        cached_company.trustpilot_rating = rep_data.get("trustpilot_rating")
        cached_company.google_search_footprint = rep_data.get("google_search_footprint")
        cached_company.last_refreshed_at = datetime.utcnow()
    else:
        new_cache = Company(
            name=company_name,
            normalized_name=normalized_query,
            cin=mca_result.get("cin"),
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
        
    await db.commit()
    
    # Merge MCA result with reputation metrics for return
    response_data = {
        **mca_result,
        "domain": domain,
        "domain_created_at": domain_age_data.get("created_at"),
        "glassdoor_rating": rep_data.get("glassdoor_rating"),
        "glassdoor_review_count": rep_data.get("glassdoor_review_count"),
        "trustpilot_rating": rep_data.get("trustpilot_rating"),
        "google_search_footprint": rep_data.get("google_search_footprint")
    }
    
    return CompanyLookupResponse(**response_data)

@router.get("/{cin}", response_model=CompanyLookupResponse)
async def get_company_by_cin(
    cin: str,
    db: AsyncSession = Depends(get_db)
):
    # Lookup by CIN directly in local cache
    stmt = select(Company).where(Company.cin == cin.strip().upper())
    result = await db.execute(stmt)
    cached_company = result.scalars().first()
    
    if not cached_company:
        raise HTTPException(
            status_code=404, 
            detail="Company not found in cache database. Perform a /search first."
        )
        
    inc_date = cached_company.incorporation_date.isoformat() if cached_company.incorporation_date else None
    filing_date = cached_company.last_filing_date.isoformat() if cached_company.last_filing_date else None
    
    return CompanyLookupResponse(
        name=cached_company.name,
        cin=cached_company.cin,
        registration_status=cached_company.registration_status,
        incorporation_date=inc_date,
        registered_address=cached_company.registered_address,
        directors=cached_company.directors,
        last_filing_date=filing_date,
        source="cache",
        match_score=1.0
    )
