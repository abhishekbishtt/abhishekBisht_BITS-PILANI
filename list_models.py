import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("No API key found")
    exit(1)

client = genai.Client(api_key=api_key)
try:
    print("Listing models...")
    for m in client.models.list(config={'page_size': 100}):
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Error: {e}")
