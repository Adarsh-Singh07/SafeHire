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

def test_general_chatbot_query():
    # Ask a general safety question
    response = client.post("/api/v1/chat/message", json={
        "message": "Should I pay money to secure a job?"
    })
    assert response.status_code == 200
    data = response.json()
    print("\n--- General Chat Response ---")
    print("Reply:", data["reply"])
    print("Grounded:", data["grounded"])
    print("Sources:", data["sources"])
    
    assert "guidelines" in "".join(data["sources"]).lower()

def test_company_rag_query():
    # 1. Search for Wipro Limited to cache it in the DB first
    client.get("/api/v1/company/search?query=Wipro Limited")
    
    # 2. Ask the chatbot about Wipro
    response = client.post("/api/v1/chat/message", json={
        "message": "When was Wipro incorporated and who are its directors?"
    })
    assert response.status_code == 200
    data = response.json()
    print("\n--- Company RAG Chat Response ---")
    print("Reply:", data["reply"])
    print("Grounded:", data["grounded"])
    print("Sources:", data["sources"])
    
    # Verify that verified RoC facts are mentioned
    assert "1945" in data["reply"]
    assert any("roc/mca" in src.lower() for src in data["sources"])

def test_company_reputation_rag_query():
    # Ask the chatbot about reviews and ratings
    response = client.post("/api/v1/chat/message", json={
        "message": "What is Wipro's Glassdoor rating according to your records?"
    })
    assert response.status_code == 200
    data = response.json()
    print("\n--- Company Reputation RAG Chat Response ---")
    print("Reply:", data["reply"])
    print("Grounded:", data["grounded"])
    print("Sources:", data["sources"])
    
    assert "3.6" in data["reply"]
    assert any("roc/mca" in src.lower() for src in data["sources"])

def test_audit_rag_query():
    # 1. Scan a scam posting to log a Safety Check in the database
    scam_payload = {
        "company_name": "Super Scam Freelancers Corp",
        "recruiter_email": "coordinator123@gmail.com",
        "raw_text": "Earn Rs 25,000 weekly doing simple form filling. Note: A registration fee of Rs 950 is required."
    }
    scan_resp = client.post("/api/v1/scan/job", json=scam_payload)
    check_id = scan_resp.json()["job_check_id"]
    
    # 2. Ask chatbot details about that scan check
    response = client.post("/api/v1/chat/message", json={
        "message": "Why is this job flagged and what was the score?",
        "job_check_id": check_id
    })
    assert response.status_code == 200
    data = response.json()
    print("\n--- Audit RAG Chat Response ---")
    print("Reply:", data["reply"])
    print("Grounded:", data["grounded"])
    print("Sources:", data["sources"])
    
    assert any(f"audit #{check_id}" in src.lower() for src in data["sources"])
    assert "950" in data["reply"] or "registration" in data["reply"].lower()

if __name__ == "__main__":
    from app.core.config import settings
    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        print("Skipping LLM chatbot tests: No API keys configured in .env")
    else:
        asyncio.run(init_db_for_test())
        try:
            test_general_chatbot_query()
            test_company_rag_query()
            test_company_reputation_rag_query()
            test_audit_rag_query()
            print("\nAll Chatbot Service RAG tests passed successfully!")
        except Exception as e:
            import traceback
            print("\nTest failed with exception:")
            traceback.print_exc()
