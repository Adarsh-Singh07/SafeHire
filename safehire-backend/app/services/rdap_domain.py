import httpx
from datetime import datetime
from typing import Dict, Any, Optional

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "outlook.com", "hotmail.com", 
    "yandex.com", "protonmail.com", "proton.me", "mail.com", "aol.com", 
    "zoho.com", "gmx.com", "icloud.com", "rediffmail.com", "live.com"
}

def extract_domain(email_or_url_or_domain: str) -> str:
    """
    Strips emails or URLs to extract the canonical host domain.
    """
    if "@" in email_or_url_or_domain:
        return email_or_url_or_domain.split("@")[-1].strip().lower()
        
    cleaned = email_or_url_or_domain.strip().lower()
    cleaned = cleaned.replace("https://", "").replace("http://", "").split("/")[0]
    cleaned = cleaned.replace("www.", "")
    return cleaned

async def lookup_domain_age(email_or_domain: str) -> Dict[str, Any]:
    """
    Queries standard Registration Data Access Protocol (RDAP) to find domain age.
    Requires no TCP port 43 access or whois command-line binaries.
    """
    domain = extract_domain(email_or_domain)
    
    result = {
        "domain": domain,
        "is_free_email": domain in FREE_EMAIL_DOMAINS,
        "created_at": None,
        "age_months": None,
        "unverified": False,
        "error": None
    }
    
    # Free public email providers are treated as mature (no registry age deductions)
    if result["is_free_email"]:
        result["age_months"] = 120
        return result
        
    url = f"https://rdap.org/domain/{domain}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=6.0, follow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                
                creation_date_str = None
                for event in events:
                    action = event.get("eventAction", "").lower()
                    if action in ["registration", "creation"]:
                        creation_date_str = event.get("eventDate")
                        break
                        
                if creation_date_str:
                    # Slice ISO time string
                    clean_date = creation_date_str.split("T")[0]
                    creation_date = datetime.strptime(clean_date, "%Y-%m-%d")
                    now = datetime.utcnow()
                    
                    diff_days = (now - creation_date).days
                    age_months = max(0, diff_days // 30)
                    
                    result["created_at"] = clean_date
                    result["age_months"] = age_months
                else:
                    result["unverified"] = True
                    result["error"] = "No creation/registration action found in RDAP event log."
            elif response.status_code == 404:
                result["unverified"] = True
                result["error"] = "Domain is unregistered or not found in RDAP system."
            else:
                result["unverified"] = True
                result["error"] = f"RDAP endpoint returned status code {response.status_code}."
    except Exception as e:
        result["unverified"] = True
        result["error"] = f"RDAP lookup failed: {str(e)}"
        
    return result
