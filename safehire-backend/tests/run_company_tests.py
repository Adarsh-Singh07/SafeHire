from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine
import asyncio

client = TestClient(app)

async def init_db_for_test():
    # Force drop and recreate tables to guarantee a clean database slate for testing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

def test_company_search_and_cache():
    # 1. Search for Wipro Limited (should hit local seed registry)
    response = client.get("/api/v1/company/search?query=Wipro Limited")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Wipro Limited"
    assert data["cin"] == "L32102KA1945PLC020800"
    assert data["registration_status"] == "Active"
    assert data["source"] == "local_fallback"
    
    # 2. Search for the exact same query again (should pull from DB CACHE)
    response_cache = client.get("/api/v1/company/search?query=Wipro Limited")
    assert response_cache.status_code == 200
    data_cache = response_cache.json()
    assert data_cache["cin"] == "L32102KA1945PLC020800"
    assert data_cache["source"] == "cache"  # Confirms cache loading works!
    print("Company search and caching verified successfully.")

def test_company_fuzzy_matching():
    # Search with minor typo ("Zenlite Solutions" instead of "Zenlyte Solutions")
    response = client.get("/api/v1/company/search?query=Zenlite Solutions")
    assert response.status_code == 200
    data = response.json()
    # Typo is small enough to clear the >= 85% threshold
    assert data["name"] == "Zenlyte Solutions Pvt Ltd"
    assert data["cin"] == "U72900KA2020PTC134567"
    print("Company fuzzy matching verified successfully.")

def test_company_not_found():
    # Search for unregistered / unknown entity
    response = client.get("/api/v1/company/search?query=Super Scam Freelancers Corp")
    assert response.status_code == 200
    data = response.json()
    assert data["unverified"] is True
    assert "error" in data
    assert data["source"] == "none"
    print("Company fallback failover verified successfully.")

if __name__ == "__main__":
    # Ensure tables are built
    asyncio.run(init_db_for_test())
    
    try:
        test_company_search_and_cache()
        test_company_fuzzy_matching()
        test_company_not_found()
        print("All Company Verification Service tests passed successfully!")
    except Exception as e:
        import traceback
        print("Test failed with exception:")
        traceback.print_exc()
