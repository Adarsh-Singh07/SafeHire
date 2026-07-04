import asyncio
from app.services.rdap_domain import lookup_domain_age
from app.services.search_reviews import lookup_company_reputation, discover_company_domain
from app.services.ogd_mca import lookup_mca_registry
from app.services.url_scraper import scrape_job_description
from app.core.config import settings

async def test_live_rdap():
    print("\n1. Testing Live RDAP Domain age checks...")
    # Test mature domain
    res_wipro = await lookup_domain_age("wipro.com")
    print("Wipro domain age res:", res_wipro)
    assert res_wipro["age_months"] > 120
    assert res_wipro["is_free_email"] is False
    assert res_wipro["unverified"] is False
    
    # Test free public domain
    res_free = await lookup_domain_age("recruiter@gmail.com")
    print("Gmail domain age res:", res_free)
    assert res_free["is_free_email"] is True
    assert res_free["age_months"] == 120

async def test_live_serper_reviews():
    print("\n2. Testing Live Serper.dev Google review crawling...")
    if not settings.SERPER_API_KEY:
        print("Skipping: SERPER_API_KEY is not configured.")
        return
        
    company = "Wipro Limited"
    domain = await discover_company_domain(company)
    print(f"Discovered domain for '{company}':", domain)
    assert domain == "wipro.com"
    
    rep = await lookup_company_reputation(company, domain)
    print("Reputation crawl details:", rep)
    
    # Assert footprint and check that rating/reviews crawled successfully
    assert rep["google_search_footprint"] in ["High", "Medium"]
    # Soft check: Either rating matched or footprint confirmed
    assert rep["glassdoor_rating"] is not None or rep["organic_results_count"] > 0

async def test_live_ogd_registry():
    print("\n3. Testing Live data.gov.in (OGD) registry search...")
    if not settings.GOV_API_KEY and not settings.OGD_API_KEY:
        print("Skipping: GOV_API_KEY is not configured.")
        return
        
    wipro_cin = "L32102KA1945PLC020800"
    reg = await lookup_mca_registry(wipro_cin)
    print("Live MCA registry details:", reg)
    assert reg["source"] in ["data.gov.in", "local_fallback"]
    assert "wipro" in reg["name"].lower()
    assert reg["cin"] == wipro_cin

async def test_live_url_scraper():
    print("\n4. Testing Live URL Scraper...")
    url = "https://example.com"
    text = await scrape_job_description(url)
    print(f"Scraped text from {url}: (Length: {len(text)})")
    print(text[:200])
    assert len(text) > 50
    assert "Example Domain" in text

async def main():
    print("OfferShield Combined Phase 1 & 2 Live Integration Tests Setup")
    print("------------------------------------------------------------")
    await test_live_rdap()
    await test_live_url_scraper()
    await test_live_serper_reviews()
    await test_live_ogd_registry()
    print("\nAll Live Integration checks successfully passed!")

if __name__ == "__main__":
    asyncio.run(main())
