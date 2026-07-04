from datetime import datetime, date
from typing import Dict, Any, Optional

def calculate_composite_safety_score(
    company_registry: Dict[str, Any],
    job_scan: Dict[str, Any],
    recruiter_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculates a deterministic 0-100 safety score for a job posting.
    Combines company registration status, LLM detected scam indicators, and contact checks.
    """
    score = 100
    explanations = []
    deductions = {}
    is_free_email = False
    
    # ─── 1. Company Registry Score Check (Max 30% Impact) ─────────────────────
    if company_registry.get("unverified"):
        deduction = 30
        score -= deduction
        deductions["registry_unverified"] = deduction
        explanations.append(
            f"Registry Check: Company details could not be verified in the public registry. (-{deduction} points)"
        )
    else:
        status = company_registry.get("registration_status", "Active")
        if status and status.lower() not in ["active", "approved"]:
            deduction = 40
            score -= deduction
            deductions["registry_inactive"] = deduction
            explanations.append(
                f"Registry Check: Company registration is listed as '{status}' (not Active). (-{deduction} points)"
            )
            
        # Check newly incorporated flag (<6 months old)
        inc_date_str = company_registry.get("incorporation_date")
        if inc_date_str:
            try:
                inc_date = datetime.strptime(inc_date_str, "%Y-%m-%d").date()
                age_days = (date.today() - inc_date).days
                if age_days < 180:
                    deduction = 15
                    score -= deduction
                    deductions["new_incorporation"] = deduction
                    explanations.append(
                        f"Registry Check: Company is newly incorporated (under 6 months old). (-{deduction} points)"
                    )
            except Exception:
                pass

    # ─── 2. Job Text Scan Score Check (LLM Risk Deductions) ───────────────────
    indicators = job_scan.get("detected_indicators", [])
    for ind in indicators:
        pattern = ind.get("pattern_name", "Unknown Risk")
        impact = ind.get("sub_score_impact", 0)
        explanation = ind.get("explanation", "")
        
        if impact > 0:
            score -= impact
            deductions[f"risk_pattern_{pattern}"] = impact
            explanations.append(
                f"Content Risk: Flagged '{pattern}' - {explanation}. (-{impact} points)"
            )

    # ─── 3. Recruiter Contact Verification (Max 15% Impact) ───────────────────
    if recruiter_email:
        email_clean = recruiter_email.strip().lower()
        free_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com", "mail.com"]
        
        is_free_email = any(email_clean.endswith(f"@{domain}") for domain in free_domains)
        if is_free_email:
            if not company_registry.get("unverified"):
                deduction = 15
                score -= deduction
                deductions["free_email_for_registered_firm"] = deduction
                explanations.append(
                    f"Recruiter Check: Free email address used for a registered company. (-{deduction} points)"
                )
            else:
                deduction = 5
                score -= deduction
                deductions["free_email_unregistered"] = deduction
                explanations.append(
                    f"Recruiter Check: Recruiter email is hosted on a free public domain. (-{deduction} points)"
                )

    # ─── 4. Domain Registration Age Check (RDAP) ──────────────────────────────
    domain_created_str = company_registry.get("domain_created_at")
    domain_age_months = company_registry.get("domain_age_months")
    
    if domain_created_str and domain_age_months is None:
        try:
            created_date = datetime.strptime(domain_created_str.split("T")[0], "%Y-%m-%d").date()
            domain_age_months = (date.today() - created_date).days // 30
        except Exception:
            pass
            
    if domain_age_months is not None:
        if domain_age_months < 6:
            deduction = 25
            score -= deduction
            deductions["domain_newly_registered"] = deduction
            explanations.append(
                f"Domain Check: Recruiter website domain is newly registered (under {domain_age_months} months old). (-{deduction} points)"
            )
            
    # Check for unverified domain state
    if recruiter_email and not is_free_email:
        if company_registry.get("domain_unverified") or company_registry.get("domain_error"):
            deduction = 35
            score -= deduction
            deductions["domain_unresolved"] = deduction
            explanations.append(
                f"Domain Check: Recruiter domain could not be resolved or registered record is missing. (-{deduction} points)"
            )

    # ─── 5. Reputation & Digital Footprint Check (Serper) ─────────────────────
    footprint = company_registry.get("google_search_footprint")
    if footprint == "Low" and not company_registry.get("unverified"):
        deduction = 20
        score -= deduction
        deductions["low_digital_footprint"] = deduction
        explanations.append(
            f"Reputation Check: Firm has a very low search footprint or web presence. (-{deduction} points)"
        )
        
    gd_rating = company_registry.get("glassdoor_rating")
    if gd_rating is not None and gd_rating < 3.0:
        deduction = 15
        score -= deduction
        deductions["low_glassdoor_rating"] = deduction
        explanations.append(
            f"Reputation Check: Low Glassdoor rating ({gd_rating} stars). (-{deduction} points)"
        )
        
    tp_rating = company_registry.get("trustpilot_rating")
    if tp_rating is not None and tp_rating < 3.0:
        deduction = 15
        score -= deduction
        deductions["low_trustpilot_rating"] = deduction
        explanations.append(
            f"Reputation Check: Low Trustpilot rating ({tp_rating} stars). (-{deduction} points)"
        )

    # Bound safety score between 0 and 100
    final_score = max(0, min(100, score))
    
    # Categorize into risk bands (FR-5.2)
    # Configurable limits: Safe (>=70), Caution (40-69), High Risk (<40)
    if final_score >= 70:
        risk_level = "Low"
    elif final_score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "High"
        
    return {
        "trust_score": final_score,
        "risk_level": risk_level,
        "deductions": deductions,
        "explanations": explanations,
        "inputs": {
            "company_registry": company_registry,
            "job_scan": job_scan,
            "recruiter_email": recruiter_email
        }
    }

def calculate_final_score(semantic_score: int, domain_data: Dict[str, Any], vector_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Legacy wrapper for analyze.py compatibility.
    """
    final_score = semantic_score
    red_flags = []
    
    if domain_data.get("is_new"):
        final_score -= 35
        red_flags.append(f"Domain is newly registered. This is a high-risk indicator.")
        
    if domain_data.get("unverified"):
        final_score -= 15
        red_flags.append(f"Domain could not be verified.")
        
    if vector_data and vector_data.get("high_confidence_match"):
        final_score -= 20
        red_flags.append("Semantic search found a high-confidence match to a known scam pattern.")
        
    final_score = max(0, min(100, final_score))
    
    if final_score >= 80:
        risk_level = "Low"
    elif final_score >= 50:
        risk_level = "Medium"
    else:
        risk_level = "High"
        
    return {
        "trust_score": final_score,
        "risk_level": risk_level,
        "domain_red_flags": red_flags
    }
