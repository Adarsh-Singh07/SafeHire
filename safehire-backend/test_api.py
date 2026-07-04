from fastapi.testclient import TestClient
from app.main import app
import sys

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("Health check passed.")

def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "OfferShield" in response.text
    print("Serve index passed.")

def test_analyze_raw_text():
    response = client.post("/api/v1/analyze/", json={"raw_text": "This is a test job description."})
    assert response.status_code == 200
    data = response.json()
    assert "trust_score" in data
    assert "risk_level" in data
    print("Analyze raw_text passed.")

def test_analyze_missing_fields():
    response = client.post("/api/v1/analyze/", json={})
    assert response.status_code == 422
    print("Analyze missing fields passed.")

if __name__ == "__main__":
    try:
        test_health()
        test_serve_index()
        
        # Test 1
        response = client.post("/api/v1/analyze/", json={"raw_text": "This is a test job description."})
        assert response.status_code == 200, f"Status code failed: {response.json()}"
        data = response.json()
        print("API Response:", data)
        # We don't assert hardcoded values for real LLM since it's dynamic
        assert "trust_score" in data
        assert "risk_level" in data
        print("Analyze raw_text passed.")
        
        test_analyze_missing_fields()
        print("All basic tests passed.")
    except AssertionError as e:
        print("Test failed:", e)
        sys.exit(1)
