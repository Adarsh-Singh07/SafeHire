from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.job_check import JobCheck
from app.models.schemas import SafetyScoreResponse, CompanyLookupResponse, JobScanResult

router = APIRouter()

@router.get("/{check_id}", response_model=SafetyScoreResponse)
async def get_safety_score_by_id(
    check_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobCheck).where(JobCheck.id == check_id)
    result = await db.execute(stmt)
    job_check = result.scalars().first()
    
    if not job_check:
        raise HTTPException(
            status_code=404, 
            detail="Safety check record not found."
        )
        
    details = job_check.details or {}
    company_verify = details.get("company_verification", {})
    scan_result_dict = details.get("job_scan", {})
    explanations = details.get("explanations", [])
    
    comp_resp = CompanyLookupResponse(**company_verify) if company_verify else None
    scan_resp = JobScanResult(**scan_result_dict) if scan_result_dict else None
    
    return SafetyScoreResponse(
        job_check_id=job_check.id,
        trust_score=job_check.composite_score,
        risk_level=job_check.risk_level,
        company_verification=comp_resp,
        job_scan=scan_resp,
        explanations=explanations
    )
