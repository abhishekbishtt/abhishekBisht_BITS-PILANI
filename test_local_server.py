import urllib.request
import urllib.error
import json
import time
import sys

def test_extraction_api():
    url = "http://localhost:8000/extract-bill-data"
    sample_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"
    
    payload = {
        "document": sample_url
    }
    
    print(f"Testing with URL: {sample_url}")
    
    try:
        # Retry logic for server startup
        max_retries = 5
        for i in range(max_retries):
            try:
                with urllib.request.urlopen("http://localhost:8000/health") as response:
                    if response.status == 200:
                        print("Server is up!")
                        break
            except (urllib.error.URLError, ConnectionRefusedError):
                print(f"Waiting for server... ({i+1}/{max_retries})")
                time.sleep(2)
        else:
            print("Server failed to start in time.")
            return

        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        
        print("Sending extraction request...")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                status_code = response.status
                response_body = response.read().decode('utf-8')
                
                print(f"Status Code: {status_code}")
                
                if status_code == 200:
                    data = json.loads(response_body)
                    print("\n--- JSON RESPONSE ANALYSIS ---")
                    print(f"Success: {data.get('is_success')}")
                    print(f"Token Usage: {data.get('token_usage')}")
                    print(f"Total Items: {data.get('data', {}).get('total_item_count')}")
                    
                    pagewise = data.get('data', {}).get('pagewise_line_items', [])
                    for page in pagewise:
                        print(f"\nPage {page.get('page_no')} ({page.get('page_type')}): {len(page.get('bill_items', []))} items")
                        for item in page.get('bill_items', []):
                            print(f"  - {item.get('item_name')}: {item.get('item_amount')} (Qty: {item.get('item_quantity')}, Rate: {item.get('item_rate')})")
                    
                    # Save response to file for analysis
                    with open("extraction_response.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print("\nFull response saved to extraction_response.json")
                else:
                    print("Failed!")
                    print(response_body)
                    
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code}")
            print(e.read().decode('utf-8'))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_extraction_api()
