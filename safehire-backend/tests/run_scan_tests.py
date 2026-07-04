from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_scan_legitimate_job():
    job_text = """
    Software Engineer - Backend
    Zenlyte Solutions Pvt Ltd - Bengaluru, Karnataka
    
    We are looking for a Backend Engineer with 2+ years of experience in Python and FastAPI.
    Responsibilities:
    - Design and develop scalable RESTful APIs.
    - Write clean, well-tested code.
    - Collaborate with front-end engineers.
    
    Requirements:
    - Strong knowledge of SQL and database indexing.
    - Experience with Docker and CI/CD pipelines.
    - Excellent communication skills.
    
    This is a full-time, on-site role in Bellandur, Bangalore. Equal opportunity employer.
    """
    
    response = client.post("/api/v1/scan/job", json={"raw_text": job_text})
    assert response.status_code == 200
    data = response.json()
    print("\n--- Legitimate Job Scan Result ---")
    print("Is Scam:", data["is_scam"])
    print("Indicators:", data["detected_indicators"])
    print("Justification:", data["justification"])
    print("Language:", data["detected_language"])
    
    assert data["is_scam"] is False
    assert data["detected_language"].lower() == "english"

def test_scan_scam_job():
    job_text = """
    URGENT HIRING: WORK FROM HOME DATA ENTRY OPERATOR!
    Earn Rs. 10,000 to Rs. 25,000 per week!
    
    No qualification required, no age limit. Laptop or mobile is enough.
    Simple copy-paste typing work. Spot selection today!
    
    Note: A registration deposit fee of Rs. 950 is required before starting for training materials and ID activation. This fee is 100% refundable with your first payout.
    
    To apply immediately, message our coordinator on Telegram: @WorkFromHomeQuickJobs
    """
    
    response = client.post("/api/v1/scan/job", json={"raw_text": job_text})
    assert response.status_code == 200
    data = response.json()
    print("\n--- Scam Job Scan Result ---")
    print("Is Scam:", data["is_scam"])
    print("Indicators:", data["detected_indicators"])
    print("Justification:", data["justification"])
    print("Language:", data["detected_language"])
    
    assert data["is_scam"] is True
    
    # Verify that upfront payment or contact patterns are flagged
    patterns = [ind["pattern_name"].lower() for ind in data["detected_indicators"]]
    print("Flagged patterns:", patterns)
    assert any("payment" in pat or "fee" in pat or "deposit" in pat or "upfront" in pat for pat in patterns)

if __name__ == "__main__":
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        print("Skipping LLM scan tests: No API keys configured in .env")
    else:
        try:
            test_scan_legitimate_job()
            test_scan_scam_job()
            print("\nAll Job Posting Scanner Service tests passed successfully!")
        except Exception as e:
            import traceback
            print("\nTest failed with exception:")
            traceback.print_exc()
