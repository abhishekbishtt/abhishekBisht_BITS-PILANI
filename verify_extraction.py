from fastapi.testclient import TestClient
from app.main import app
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

client = TestClient(app)

def test_extraction_api():
    sample_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
    
    payload = {
        "document": sample_url
    }
    
    print(f"Testing with URL: {sample_url}")
    
    response = client.post("/extract-bill-data", json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        print(f"Token Usage: {data['token_usage']}")
        print(f"Total Items: {data['data']['total_item_count']}")
        
        for page in data['data']['pagewise_line_items']:
            print(f"Page {page['page_no']} ({page['page_type']}): {len(page['bill_items'])} items")
            for item in page['bill_items']:
                print(f"  - {item['item_name']}: {item['item_amount']}")
    else:
        print("Failed!")
        print(response.text)

if __name__ == "__main__":
    test_extraction_api()
