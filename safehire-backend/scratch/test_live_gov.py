import os
import httpx
import asyncio
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

async def test_live_mca():
    # Load settings/env keys
    gov_key = os.getenv("GOV_API_KEY", "")
    company_name = "Bisani Brothers Private Limited"
    
    resource_id = "4dbe5667-7b6b-41d7-82af-211562424d9a"
    base_url = f"https://api.data.gov.in/resource/{resource_id}"
    
    # Try without filters first to test raw latency and inspect the real schema fields
    params = {
        "api-key": gov_key,
        "format": "json",
        "limit": 2
    }
    
    print(f"Testing OGD request with NO filters...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(base_url, params=params, timeout=12.0)
            print("Status Code:", response.status_code)
            print("Raw Headers:", dict(response.headers))
            
            # Print body snippet
            body = response.text
            print("\nResponse Body Snippet (500 chars):")
            print(body[:500])
        except Exception as e:
            import traceback
            print("HTTP Request Exception:", repr(e))
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_live_mca())
