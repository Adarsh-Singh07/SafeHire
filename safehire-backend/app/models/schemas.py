from pydantic import BaseModel, HttpUrl, model_validator
from typing import Optional, List

class JobAnalysisRequest(BaseModel):
    url: Optional[HttpUrl] = None
    raw_text: Optional[str] = None
    company_name: Optional[str] = None
    recruiter_email: Optional[str] = None

    @model_validator(mode='after')
    def check_url_or_text(self) -> 'JobAnalysisRequest':
        if not self.url and not self.raw_text:
            raise ValueError('Either url or raw_text must be provided')
        return self

class ScrapeResult(BaseModel):
    title: str
    company: Optional[str] = None
    raw_description: str
    links_found: List[str] = []

class TrustScoreResponse(BaseModel):
    trust_score: int
    risk_level: str
    summary: str
    red_flags: List[str] = []

class CompanyLookupResponse(BaseModel):
    name: Optional[str] = None
    cin: Optional[str] = None
    registration_status: Optional[str] = None
    incorporation_date: Optional[str] = None
    registered_address: Optional[str] = None
    directors: Optional[str] = None
    last_filing_date: Optional[str] = None
    unverified: bool = False
    error: Optional[str] = None
    match_score: float = 0.0
    suggested_match: Optional[dict] = None
    source: str = "none"
    
    # New combined reputation and domain properties
    domain: Optional[str] = None
    domain_created_at: Optional[str] = None
    glassdoor_rating: Optional[float] = None
    glassdoor_review_count: Optional[int] = None
    trustpilot_rating: Optional[float] = None
    google_search_footprint: Optional[str] = None

class RiskIndicator(BaseModel):
    pattern_name: str
    explanation: str
    sub_score_impact: int

class JobScanResult(BaseModel):
    is_scam: bool
    detected_indicators: List[RiskIndicator] = []
    justification: str
    detected_language: str = "English"

class SafetyScoreResponse(BaseModel):
    job_check_id: str
    trust_score: int
    risk_level: str
    company_verification: Optional[CompanyLookupResponse] = None
    job_scan: Optional[JobScanResult] = None
    explanations: List[str] = []

class ChatMessageRequest(BaseModel):
    message: str
    job_check_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    reply: str
    grounded: bool
    sources: List[str] = []
