import httpx
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any
import dateutil.parser

async def analyze_domain(url: str) -> Dict[str, Any]:
    """
    Checks the age and safety of the employer's domain.
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        if not domain:
            return {"is_new": False, "unverified": True, "error": "Invalid URL"}
            
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Extract root domain roughly (works for most common TLDs)
        parts = domain.split(".")
        if len(parts) > 2:
            domain = ".".join(parts[-2:])
            
        rdap_url = f"https://rdap.org/domain/{domain}"
        
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(rdap_url)
            
            if response.status_code != 200:
                return {"is_new": False, "unverified": True, "error": f"RDAP lookup failed with status {response.status_code}"}
                
            data = response.json()
            events = data.get("events", [])
            
            creation_date_str = None
            for event in events:
                if event.get("eventAction") == "registration":
                    creation_date_str = event.get("eventDate")
                    break
                    
            if not creation_date_str:
                return {"is_new": False, "unverified": True, "error": "No registration date found"}
                
            creation_date = dateutil.parser.isoparse(creation_date_str)
            now = datetime.now(timezone.utc)
            
            # Calculate months diff
            diff_days = (now - creation_date).days
            diff_months = diff_days / 30.0
            
            is_new = diff_months < 6
            
            return {
                "age_months": int(diff_months),
                "is_new": is_new,
                "unverified": False,
                "creation_date": creation_date_str,
                "domain": domain
            }
            
    except Exception as e:
        return {"is_new": False, "unverified": True, "error": str(e)}
