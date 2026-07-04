import httpx
import re
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings
from app.core.normalization import normalize_company_name, get_similarity_ratio

# Local fallback seed registry - major Indian corporations
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
        "name": "HCL Technologies Limited",
        "cin": "L74140DL1991PLC046369",
        "registration_status": "Active",
        "incorporation_date": "1991-11-12",
        "registered_address": "806, Siddharth, 96, Nehru Place, New Delhi, Delhi, 110019",
        "directors": "C Vijayakumar, Shiv Nadar",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Tech Mahindra Limited",
        "cin": "L64200MH1986PLC041370",
        "registration_status": "Active",
        "incorporation_date": "1986-10-24",
        "registered_address": "Gateway Building, Apollo Bunder, Mumbai, Maharashtra, 400001",
        "directors": "Mohit Joshi, Anand Mahindra",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Capgemini Technology Services India Limited",
        "cin": "U72200MH1997PLC107131",
        "registration_status": "Active",
        "incorporation_date": "1997-08-22",
        "registered_address": "21st Floor, DLF Cyber City, DLF Phase 2, Gurugram, Haryana, 122002",
        "directors": "Aiman Ezzat, Salil Parekh",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Accenture Solutions Private Limited",
        "cin": "U72200KA1997PTC022153",
        "registration_status": "Active",
        "incorporation_date": "1997-04-01",
        "registered_address": "71, Cunningham Road, Bengaluru, Karnataka, 560052",
        "directors": "Julie Sweet, Rekha Menon",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "IBM India Private Limited",
        "cin": "U30007KA1997PTC022381",
        "registration_status": "Active",
        "incorporation_date": "1997-04-01",
        "registered_address": "3rd Floor, Tower C, Embassy Golf Links, Bengaluru, Karnataka, 560071",
        "directors": "Sandip Patel, Arvind Krishna",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Deloitte Touche Tohmatsu India LLP",
        "cin": "AAC-1983",
        "registration_status": "Active",
        "incorporation_date": "1983-01-01",
        "registered_address": "One India Bulls Centre, Tower 2B, 841, Senapati Bapat Marg, Mumbai, Maharashtra, 400013",
        "directors": "Romal Shetty, N. Venkatram",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Cognizant Technology Solutions India Private Limited",
        "cin": "U72200TN1994PTC028081",
        "registration_status": "Active",
        "incorporation_date": "1994-01-26",
        "registered_address": "5/535, Old Mahabalipuram Road, Sholinganallur, Chennai, Tamil Nadu, 600119",
        "directors": "Ravi Kumar S, Balu Doraisamy",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Mphasis Limited",
        "cin": "L30007KA2000PLC025294",
        "registration_status": "Active",
        "incorporation_date": "2000-06-01",
        "registered_address": "Bagmane World Technology Center, Marathahalli, Bengaluru, Karnataka, 560037",
        "directors": "Nitin Rakesh, Davinder Singh Brar",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Larsen and Toubro Infotech Limited",
        "cin": "L72900MH2001PLC132761",
        "registration_status": "Active",
        "incorporation_date": "2001-12-27",
        "registered_address": "L&T Technology Centre, Saki Vihar Road, Powai, Mumbai, Maharashtra, 400072",
        "directors": "Sanjay Jalona, S N Subrahmanyan",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Oracle India Private Limited",
        "cin": "U72900MH1997PTC107314",
        "registration_status": "Active",
        "incorporation_date": "1997-03-15",
        "registered_address": "Floor 15, Tower 2, One Indiabulls Centre, Lower Parel, Mumbai, Maharashtra, 400013",
        "directors": "Shailender Kumar, Larry Ellison",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Microsoft Corporation India Private Limited",
        "cin": "U74140DL1996PTC077258",
        "registration_status": "Active",
        "incorporation_date": "1996-01-03",
        "registered_address": "Microsoft Signature Building, IGI Airport Tech Zone, New Delhi, Delhi, 110037",
        "directors": "Satya Nadella, Anant Maheshwari",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Amazon Development Centre India Private Limited",
        "cin": "U72200KA2005PTC036021",
        "registration_status": "Active",
        "incorporation_date": "2005-05-16",
        "registered_address": "Brigade Gateway, 8th Floor, 26/1, Dr. Rajkumar Road, Bengaluru, Karnataka, 560055",
        "directors": "Andy Jassy, Manish Tiwary",
        "last_filing_date": "2025-03-31"
    },
    {
        "name": "Flipkart Internet Private Limited",
        "cin": "U51109KA2012PTC066107",
        "registration_status": "Active",
        "incorporation_date": "2012-10-05",
        "registered_address": "Ozone Manay Tech Park, #56/18 & 55/09, 7th Floor, Hosur Road, Bengaluru, Karnataka, 560068",
        "directors": "Kalyan Krishnamurthy, Binny Bansal",
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
    Multi-source fallback using Serper.dev Google Search to find company registry data.
    Tries ZaubaCorp, Tofler, and broad Google searches. Returns best match found.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key:
        return None

    search_url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    cin_pattern = re.compile(r'\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b')

    best_result = None
    best_score = 0.0

    # Multiple query strategies in priority order
    queries = [
        f'site:zaubacorp.com "{company_name}"',
        f'site:zaubacorp.com {company_name} company',
        f'site:tofler.in "{company_name}"',
        f'"{company_name}" CIN incorporated India MCA company',
    ]

    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                response = await client.post(search_url, json={"q": query}, headers=headers, timeout=8.0)
                if response.status_code != 200:
                    continue
                organic = response.json().get("organic", [])
                if not organic:
                    continue

                for res in organic[:3]:
                    title = res.get("title", "")
                    snippet = res.get("snippet", "")
                    link = res.get("link", "")
                    full_text = f"{title} {snippet} {link}"

                    # Clean title: "COMPANY NAME | ZaubaCorp" -> "COMPANY NAME"
                    clean_title = title.split("|")[0].split(" - ")[0].strip()

                    # Normalise both for comparison, strip common legal suffixes
                    def _strip_suffixes(s: str) -> str:
                        for sfx in ["private limited", "pvt ltd", "pvt. ltd.", "limited", " ltd", " llp"]:
                            s = s.replace(sfx, "").strip()
                        return s

                    clean_norm = _strip_suffixes(normalize_company_name(clean_title))
                    query_norm = _strip_suffixes(normalize_company_name(company_name))
                    similarity = get_similarity_ratio(query_norm, clean_norm)

                    # Substring check: "capgemini" inside "capgemini technology services india"
                    substring_match = (query_norm and clean_norm and
                                       (query_norm in clean_norm or clean_norm in query_norm))

                    effective_score = max(similarity, 0.72 if substring_match else 0.0)

                    if effective_score < 0.55:
                        continue  # Skip clearly wrong results

                    # Extract CIN
                    cin_match = cin_pattern.search(full_text)
                    cin = cin_match.group(1) if cin_match else None

                    # Extract incorporation date
                    inc_date = None
                    date_patterns = [
                        r'incorporated\s+on\s+([\d\w\s,]+?)[\.\|\n]',
                        r'date\s+of\s+(?:incorporation|registration)[:\s]+([\d\w\s,]+?)[\.\|\n]',
                        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
                        r'(\d{4}-\d{2}-\d{2})',
                    ]
                    for pat in date_patterns:
                        m = re.search(pat, full_text, re.IGNORECASE)
                        if m:
                            raw = m.group(1).strip()
                            for fmt in ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d-%m-%Y"]:
                                try:
                                    inc_date = datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    continue
                            if inc_date:
                                break

                    # Registration status
                    status = "Active"
                    if re.search(r'struck[- ]off|dissolved|inactive|wound up', full_text, re.IGNORECASE):
                        status = "Struck-Off"
                    elif re.search(r'dormant', full_text, re.IGNORECASE):
                        status = "Dormant"

                    if effective_score > best_score:
                        best_score = effective_score
                        source_site = (
                            "zaubacorp.com" if "zaubacorp" in link else
                            "tofler.in" if "tofler" in link else
                            "google_search"
                        )
                        best_result = {
                            "name": clean_title if clean_title else company_name,
                            "cin": cin,
                            "registration_status": status,
                            "incorporation_date": inc_date,
                            "registered_address": f"See official profile: {link}",
                            "directors": f"See official profile: {link}",
                            "last_filing_date": None,
                            "source": source_site,
                            "match_score": round(effective_score, 2),
                        }

            except Exception as e:
                print(f"OfferShield Search Fallback Error [{query[:50]}]: {str(e)}")
                continue

    if best_result:
        print(f"OfferShield Search Fallback: Matched '{best_result['name']}' "
              f"(score={best_result['match_score']}, cin={best_result['cin']}, source={best_result['source']})")
    return best_result

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
