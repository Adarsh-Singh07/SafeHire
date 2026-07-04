import httpx
import re
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.core.normalization import normalize_company_name, get_similarity_ratio

# Local fallback seed registry dataset representing standard Indian corporations
MOCK_OGD_REGISTRY = [
    {
        "name": "Tata Consultancy Services Limited",
        "cin": "L72200MH1995PLC087052",
        "registration_status": "Active",
        "incorporation_date": "1995-01-26",
        "registered_address": "9th Floor, Nirmal Building, Nariman Point, Mumbai, Maharashtra, 400021",
        "directors": "K. Krithivasan, N. Chandrasekaran",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Infosys Limited",
        "cin": "L85110KA1981PLC013115",
        "registration_status": "Active",
        "incorporation_date": "1981-07-02",
        "registered_address": "Electronics City, Hosur Road, Bengaluru, Karnataka, 560100",
        "directors": "Salil Parekh, Nandan Nilekani",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Wipro Limited",
        "cin": "L32102KA1945PLC020800",
        "registration_status": "Active",
        "incorporation_date": "1945-12-29",
        "registered_address": "Doddakannelli, Sarjapur Road, Bengaluru, Karnataka, 560035",
        "directors": "Srinivas Pallia, Rishad Premji",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Zenlyte Solutions Pvt Ltd",
        "cin": "U72900KA2020PTC134567",
        "registration_status": "Active",
        "incorporation_date": "2020-05-20",
        "registered_address": "123 Tech Park, Bellandur, Bengaluru, Karnataka, 560103",
        "directors": "Adarsh Singh, John Doe",
        "last_filing_date": "2025-09-30"
    },
    {
        "name": "QuickJob Data Entry Services Pvt Ltd",
        "cin": "U74999DL2026PTC999999",
        "registration_status": "Active",
        "incorporation_date": "2026-03-01",
        "registered_address": "Flat 402, Pocket B, Janakpuri, New Delhi, 110058",
        "directors": "Rajesh Kumar",
        "last_filing_date": ""
    },
    {
        "name": "Apex Fraudulent Solutions LLP",
        "cin": None,
        "registration_status": "Struck-Off",
        "incorporation_date": "2018-10-10",
        "registered_address": "Virtual Office 12, Cyber Hub, Gurugram, Haryana",
        "directors": "Scammy Director",
        "last_filing_date": "2020-01-01"
    }
]

async def lookup_mca_via_search(company_name: str) -> Optional[Dict[str, Any]]:
    """
    Fallback crawler using Serper.dev Google Search to find company indexes on ZaubaCorp.
    Extracts CIN and incorporation dates directly from snippets in real-time.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key:
        return None
    try:
        query = f'site:zaubacorp.com "{company_name}"'
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"q": query}, headers=headers, timeout=6.0)
            if response.status_code == 200:
                organic = response.json().get("organic", [])
                if organic:
                    first_res = organic[0]
                    title = first_res.get("title", "")
                    snippet = first_res.get("snippet", "")
                    link = first_res.get("link", "")
                    
                    # Clean title: e.g. "BISANI BROTHERS PRIVATE LIMITED | ZaubaCorp" -> "BISANI BROTHERS PRIVATE LIMITED"
                    clean_title = title.split("|")[0].strip()
                    similarity = get_similarity_ratio(normalize_company_name(company_name), normalize_company_name(clean_title))
                    
                    if similarity >= 0.80:
                        # Extract CIN (21-character alphanumeric code)
                        cin_match = re.search(r'\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b', link + " " + snippet)
                        cin = cin_match.group(1) if cin_match else None
                        
                        # Extract Date (e.g. "19 Dec 2017")
                        date_match = re.search(r'incorporated on\s+([\d\w\s]+?)\.', snippet, re.IGNORECASE)
                        inc_date_raw = date_match.group(1) if date_match else None
                        
                        # Standardize date format: "19 Dec 2017" -> "2017-12-19"
                        inc_date = None
                        if inc_date_raw:
                            date_cleaned = inc_date_raw.strip()
                            parsed_date = None
                            for fmt in ["%d %b %Y", "%d %B %Y", "%Y-%m-%d"]:
                                try:
                                    parsed_date = datetime.strptime(date_cleaned, fmt)
                                    break
                                except ValueError:
                                    continue
                            if parsed_date:
                                inc_date = parsed_date.strftime("%Y-%m-%d")
                                
                        address = f"Verified registered address on official profile: {link}"
                        directors = f"Verified directors on official profile: {link}"
                        
                        print(f"OfferShield Search Fallback: Successfully matched registry details for '{clean_title}' via ZaubaCorp!")
                        return {
                            "name": clean_title,
                            "cin": cin,
                            "registration_status": "Active",
                            "incorporation_date": inc_date,
                            "registered_address": address,
                            "directors": directors,
                            "last_filing_date": None,
                            "source": "zaubacorp.com",
                            "match_score": similarity
                        }
    except Exception as e:
        print(f"OfferShield Search Fallback Connection Error: {str(e)}")
    return None

async def lookup_mca_registry(query: str, ogd_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Looks up a company in the MCA registry.
    Queries the live data.gov.in OGD registry,
    falls back to live ZaubaCorp index searches,
    and falls back to local seeds if all network connections timeout.
    """
    api_key = ogd_api_key or settings.GOV_API_KEY or settings.OGD_API_KEY
    clean_query = query.strip().upper()
    normalized_query = normalize_company_name(query)
    
    # 1. Query live data.gov.in OGD REST portal if key is active
    if api_key:
        try:
            is_cin = len(clean_query) == 21 and re.match(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", clean_query)
            resource_id = "4dbe5667-7b6b-41d7-82af-211562424d9a"
            base_url = f"https://api.data.gov.in/resource/{resource_id}"
            
            params = {
                "api-key": api_key,
                "format": "json",
                "limit": 5
            }
            
            if is_cin:
                params["filters[cin]"] = clean_query
            else:
                params["filters[company_name]"] = clean_query
                
            print(f"OfferShield OGD Client: Fetching from data.gov.in (is_cin={is_cin})...")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, params=params, timeout=6.0)
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    
                    if not records and not is_cin:
                        params.pop("filters[company_name]", None)
                        params["filters[companyName]"] = clean_query
                        response = await client.get(base_url, params=params, timeout=6.0)
                        if response.status_code == 200:
                            data = response.json()
                            records = data.get("records", [])
                            
                    if records:
                        rec = records[0]
                        comp_name = rec.get("company_name") or rec.get("companyName") or clean_query
                        comp_status = rec.get("company_status") or rec.get("companyStatus") or rec.get("company_category") or "Active"
                        inc_date = rec.get("date_of_registration") or rec.get("incorporationDate") or rec.get("registration_date")
                        address = rec.get("registered_office_address") or rec.get("registeredAddress") or rec.get("address")
                        directors_list = rec.get("directors_list") or rec.get("directors") or "Unknown"
                        filing_date = rec.get("last_annual_filing_date") or rec.get("lastFilingDate")
                        
                        return {
                            "name": comp_name,
                            "cin": rec.get("cin"),
                            "registration_status": comp_status,
                            "incorporation_date": inc_date,
                            "registered_address": address,
                            "directors": directors_list,
                            "last_filing_date": filing_date,
                            "source": "data.gov.in",
                            "match_score": 1.0
                        }
        except Exception as e:
            print(f"SafeHire OGD Connection Error (failing over to search index): {str(e)}")

    # 2. Query live Google Search/ZaubaCorp directory index (High-Availability live lookup)
    # Check if query looks like a company name (not a CIN)
    is_cin_query = len(clean_query) == 21 and re.match(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", clean_query)
    if not is_cin_query:
        search_fallback = await lookup_mca_via_search(query)
        if search_fallback:
            return search_fallback

    # 3. Local fallback matching (SQLite mock / fallback database check)
    for company in MOCK_OGD_REGISTRY:
        if company["cin"] == clean_query:
            return {**company, "source": "local_fallback", "match_score": 1.0}
            
    best_match = None
    highest_score = 0.0
    
    for company in MOCK_OGD_REGISTRY:
        norm_company_name = normalize_company_name(company["name"])
        score = get_similarity_ratio(normalized_query, norm_company_name)
        
        if normalized_query == norm_company_name:
            return {**company, "source": "local_fallback", "match_score": 1.0}
            
        if score > highest_score:
            highest_score = score
            best_match = company
            
    if highest_score >= 0.85:
        return {**best_match, "source": "local_fallback", "match_score": highest_score}
    elif highest_score >= 0.80:
        return {
            "suggested_match": best_match,
            "match_score": highest_score,
            "source": "local_suggestion"
        }
        
    return {
        "unverified": True,
        "error": "No verified company registry records found under this name or CIN.",
        "source": "none",
        "match_score": 0.0
    }
