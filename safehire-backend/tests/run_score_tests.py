from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine
import asyncio

client = TestClient(app)

async def init_db_for_test():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

def test_score_and_audit():
    # --- Test Case 1: Legitimate Company + Business Email + Safe Content ---
    safe_payload = {
        "company_name": "Zenlyte Solutions Pvt Ltd",
        "recruiter_email": "hr@zenlyte.com",
        "raw_text": "We are seeking a Python Developer with 2 years of experience. Fully on-site role in Bangalore."
    }
    
    response = client.post("/api/v1/scan/job", json=safe_payload)
    assert response.status_code == 200
    data = response.json()
    print("\n--- Safe Job Audit ---")
    print("Job Check ID:", data["job_check_id"])
    print("Composite Score:", data["trust_score"])
    print("Risk Level:", data["risk_level"])
    print("Explanations:", data["explanations"])
    
    assert data["trust_score"] >= 70
    assert data["risk_level"] == "Low"

    # --- Test Case 2: Unverified Company + Free Email + High-Risk Scam Content ---
    scam_payload = {
        "company_name": "Super Scam Freelancers Corp",
        "recruiter_email": "coordinator123@gmail.com",
        "raw_text": "WORK FROM HOME DATA ENTRY! Earn Rs 25,000 weekly! Simple typing tasks. Spot hiring. Note: A registration fee of Rs 950 is required before starting."
    }
    
    response_scam = client.post("/api/v1/scan/job", json=scam_payload)
    assert response_scam.status_code == 200
    data_scam = response_scam.json()
    print("\n--- Scam Job Audit ---")
    print("Job Check ID:", data_scam["job_check_id"])
    print("Composite Score:", data_scam["trust_score"])
    print("Risk Level:", data_scam["risk_level"])
    print("Explanations:", data_scam["explanations"])
    
    # Assert deterministic risk deductions
    assert data_scam["trust_score"] < 40
    assert data_scam["risk_level"] == "High"
    assert len(data_scam["explanations"]) >= 3
    
    scam_check_id = data_scam["job_check_id"]

    # --- Test Case 3: Retrieve Audit Log by ID ---
    response_retrieve = client.get(f"/api/v1/score/{scam_check_id}")
    assert response_retrieve.status_code == 200
    data_retrieve = response_retrieve.json()
    print("\n--- Retrieved Audit Log ---")
    print("Retrieved Score:", data_retrieve["trust_score"])
    print("Retrieved Risk Level:", data_retrieve["risk_level"])
    print("Retrieved Explanations:", data_retrieve["explanations"])
    
    assert data_retrieve["trust_score"] == data_scam["trust_score"]
    assert data_retrieve["risk_level"] == data_scam["risk_level"]
    assert data_retrieve["company_verification"]["unverified"] is True

if __name__ == "__main__":
    from app.core.config import settings
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        print("Skipping LLM score tests: No API keys configured in .env")
    else:
        asyncio.run(init_db_for_test())
        try:
            test_score_and_audit()
            print("\nAll Safety Score Calculator tests passed successfully!")
        except Exception as e:
            import traceback
            print("\nTest failed with exception:")
            traceback.print_exc()
