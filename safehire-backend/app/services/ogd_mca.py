import httpx
import re
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.normalization import normalize_company_name, get_similarity_ratio

# Local fallback registry dataset representing standard Indian corporations and scam flags
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
        "incorporation_date": "2026-03-01",  # Newly registered (< 6 months old)
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
    },
    {
        "name": "Bisani Brothers Private Limited",
        "cin": "U51909WB1998PTC086421",
        "registration_status": "Active",
        "incorporation_date": "1998-02-10",
        "registered_address": "45 Chowringhee Road, Kolkata, West Bengal, 700071",
        "directors": "Rajesh Bisani, Amit Bisani",
        "last_filing_date": "2025-03-31"
    }
]

async def lookup_mca_registry(query: str, ogd_api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Looks up a company in the MCA registry.
    Queries the live data.gov.in OGD registry (using the RoC Company Master Data resource),
    with a graceful local seed fallback.
    """
    # Use key from arguments or settings
    api_key = ogd_api_key or settings.GOV_API_KEY or settings.OGD_API_KEY
    clean_query = query.strip().upper()
    normalized_query = normalize_company_name(query)
    
    # 1. Query live data.gov.in OGD REST portal if key is active
    if api_key:
        try:
            # Build filters dynamically depending on query format
            # Indian Corporate Identification Number (CIN) is exactly 21 characters
            is_cin = len(clean_query) == 21 and re.match(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$", clean_query)
            
            # Base OGD resource URL for RoC Company Master Data
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
                # OGD schemas can vary between company_name and companyName
                params["filters[company_name]"] = clean_query
                
            print(f"OfferShield OGD Client: Fetching from data.gov.in (is_cin={is_cin})...")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(base_url, params=params, timeout=8.0)
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("records", [])
                    
                    # If we searched by company_name and got nothing, try companyName filter
                    if not records and not is_cin:
                        params.pop("filters[company_name]", None)
                        params["filters[companyName]"] = clean_query
                        response = await client.get(base_url, params=params, timeout=8.0)
                        if response.status_code == 200:
                            data = response.json()
                            records = data.get("records", [])
                            
                    if records:
                        rec = records[0]
                        # Handle variant casing across OGD schema revisions
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
            print(f"SafeHire OGD Connection Error (failing over to local registry): {str(e)}")

    # 2. Local fallback matching (SQLite mock / fallback database check)
    # Check if exact CIN match
    for company in MOCK_OGD_REGISTRY:
        if company["cin"] == clean_query:
            return {**company, "source": "local_fallback", "match_score": 1.0}
            
    # Fuzzy name matching
    best_match = None
    highest_score = 0.0
    
    for company in MOCK_OGD_REGISTRY:
        norm_company_name = normalize_company_name(company["name"])
        score = get_similarity_ratio(normalized_query, norm_company_name)
        
        # Exact match after suffix stripping
        if normalized_query == norm_company_name:
            return {**company, "source": "local_fallback", "match_score": 1.0}
            
        if score > highest_score:
            highest_score = score
            best_match = company
            
    # Apply fuzzy thresholds
    if highest_score >= 0.85:
        return {**best_match, "source": "local_fallback", "match_score": highest_score}
    elif highest_score >= 0.80:
        return {
            "suggested_match": best_match,
            "match_score": highest_score,
            "source": "local_suggestion"
        }
        
    # Unverified
    return {
        "unverified": True,
        "error": "No verified company registry records found under this name or CIN.",
        "source": "none",
        "match_score": 0.0
    }
