import httpx
import re
from typing import Dict, Any, Optional
from app.core.config import settings

def parse_rating_from_snippet(snippet: str) -> Optional[float]:
    """
    Extracts numerical rating (e.g. 4.2) from search result snippet text.
    """
    # Pattern 1: "Rating: 4.1" or "Rating: 4"
    match = re.search(r"Rating:\s*(\d+(?:\.\d+)?)", snippet, re.IGNORECASE)
    if match:
        return float(match.group(1))
        
    # Pattern 2: "4.1 stars" or "4.1 out of 5"
    match = re.search(r"\b([1-5]\.[0-9])\s*(?:star|out of 5)", snippet, re.IGNORECASE)
    if match:
        return float(match.group(1))
        
    # Pattern 3: "4/5" or "4.2/5"
    match = re.search(r"\b([1-5](?:\.[0-9])?)\s*/\s*5", snippet)
    if match:
        return float(match.group(1))
        
    return None

def parse_reviews_count_from_snippet(snippet: str) -> Optional[int]:
    """
    Extracts review count (e.g. 1,250 reviews) from search snippet text.
    """
    match = re.search(r"(\d+(?:,\d+)*)\s*reviews", snippet, re.IGNORECASE)
    if match:
        clean_num = match.group(1).replace(",", "")
        return int(clean_num)
    return None

async def lookup_company_reputation(company_name: str, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Searches Glassdoor and Trustpilot for the company reviews using Serper.dev search.
    """
    api_key = settings.SERPER_API_KEY
    result = {
        "glassdoor_rating": None,
        "glassdoor_review_count": 0,
        "trustpilot_rating": None,
        "google_search_footprint": "Low", # Default if no search index matches
        "organic_results_count": 0
    }
    
    if not api_key:
        print("OfferShield Rep Client: Serper API key not configured. Skipping live search.")
        return result
        
    async with httpx.AsyncClient() as client:
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        
        # Query 1: Glassdoor rating search
        try:
            gd_query = f'site:glassdoor.co.in/ "{company_name}" reviews'
            payload = {"q": gd_query}
            response = await client.post("https://google.serper.dev/search", json=payload, headers=headers, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                organic = data.get("organic", [])
                result["organic_results_count"] += len(organic)
                if organic:
                    first_res = organic[0]
                    snippet = first_res.get("snippet", "")
                    title = first_res.get("title", "")
                    full_text = f"{title} {snippet}"
                    
                    # 1. Try Serper structured fields
                    rating = first_res.get("rating")
                    reviews = first_res.get("ratingCount") or first_res.get("reviewCount") or first_res.get("votes")
                    
                    if rating:
                        try:
                            result["glassdoor_rating"] = float(rating)
                        except ValueError:
                            pass
                    if reviews:
                        try:
                            if isinstance(reviews, str):
                                clean_rev = reviews.replace(",", "").replace("K", "000").split(".")[0]
                                result["glassdoor_review_count"] = int(clean_rev)
                            else:
                                result["glassdoor_review_count"] = int(reviews)
                        except ValueError:
                            pass
                            
                    # 2. Fallback to regex
                    if result["glassdoor_rating"] is None:
                        result["glassdoor_rating"] = parse_rating_from_snippet(full_text)
                    if result["glassdoor_review_count"] == 0:
                        parsed_rev = parse_reviews_count_from_snippet(full_text)
                        if parsed_rev:
                            result["glassdoor_review_count"] = parsed_rev
        except Exception as e:
            print(f"Error checking Glassdoor reputation: {str(e)}")
            
        # Query 2: Trustpilot review search
        try:
            tp_term = domain or company_name
            tp_query = f'site:trustpilot.com/review "{tp_term}"'
            payload = {"q": tp_query}
            response = await client.post("https://google.serper.dev/search", json=payload, headers=headers, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                organic = data.get("organic", [])
                result["organic_results_count"] += len(organic)
                if organic:
                    first_res = organic[0]
                    snippet = first_res.get("snippet", "")
                    title = first_res.get("title", "")
                    full_text = f"{title} {snippet}"
                    
                    # 1. Try Serper structured fields
                    rating = first_res.get("rating")
                    if rating:
                        try:
                            result["trustpilot_rating"] = float(rating)
                        except ValueError:
                            pass
                            
                    # 2. Fallback to regex
                    if result["trustpilot_rating"] is None:
                        result["trustpilot_rating"] = parse_rating_from_snippet(full_text)
        except Exception as e:
            print(f"Error checking Trustpilot reputation: {str(e)}")
            
        # Footprint categorization
        if result["organic_results_count"] >= 4:
            result["google_search_footprint"] = "High"
        elif result["organic_results_count"] >= 1:
            result["google_search_footprint"] = "Medium"
            
    return result

async def discover_company_domain(company_name: str) -> Optional[str]:
    """
    Searches Google for the company name to discover its official website domain.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {"q": f"{company_name} official website"}
            response = await client.post("https://google.serper.dev/search", json=payload, headers=headers, timeout=6.0)
            if response.status_code == 200:
                organic = response.json().get("organic", [])
                if organic:
                    link = organic[0].get("link", "")
                    return extract_domain(link)
    except Exception as e:
        print(f"Error discovering domain for {company_name}: {str(e)}")
    return None

def extract_domain(url: str) -> str:
    cleaned = url.strip().lower()
    cleaned = cleaned.replace("https://", "").replace("http://", "").split("/")[0]
    cleaned = cleaned.replace("www.", "")
    return cleaned
