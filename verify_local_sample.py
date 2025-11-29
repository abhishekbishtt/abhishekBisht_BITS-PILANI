import json
from fastapi.testclient import TestClient
from app.main import app

def verify_sample():
    client = TestClient(app)
    # URL pointing to the file served by python -m http.server 8000
    sample_url = "http://localhost:8000/train_sample_1.pdf"
    
    print(f"Testing with URL: {sample_url}")
    
    try:
        response = client.post("/extract-bill-data", json={"document": sample_url})
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=4))
        else:
            print(f"Failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_sample()
