# Medical Bill Extraction API

A high-performance, serverless REST API for extracting structured line items from medical bills (PDFs and images) using Google Gemini 2.0 Flash.

## 🚀 Features

-   **AI-Powered Extraction**: Uses Google's `gemini-2.0-flash-exp` for context-aware data extraction.
-   **High Concurrency**: Processes pages in parallel (up to 10 concurrent requests) for sub-40s response times.
-   **Smart Batching**: Handles large PDFs by splitting them into batches of 5 pages.
-   **Context Awareness**: Passes extracted items from previous pages to the LLM to prevent duplicates and maintain context.
-   **Optimized Performance**:
    -   Reduced PDF DPI (150) for faster conversion.
    -   Lightweight image processing (no heavy OpenCV operations).
    -   Async I/O for all network and file operations.
-   **Serverless**: Deployed on Google Cloud Run for auto-scaling and zero maintenance.

## 🛠️ Tech Stack

-   **Language**: Python 3.13
-   **Framework**: FastAPI (Async)
-   **LLM**: Google Gemini 2.0 Flash (`google-genai` SDK)
-   **Image Processing**: `pdf2image`, `Pillow`
-   **Containerization**: Docker
-   **Cloud**: Google Cloud Run

## 📂 Project Structure

```
.
├── app/
│   ├── api/            # API routes
│   ├── core/           # Config and constants
│   ├── models/         # Pydantic models
│   ├── services/       # Business logic (Gemini, Document, Extraction)
│   └── utils/          # Helper functions
├── deploy.sh           # Deployment script for Cloud Run
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## ⚡ Quick Start

### Prerequisites

-   Python 3.11+
-   Google Cloud SDK (`gcloud`)
-   Gemini API Key

### Local Development

1.  **Clone the repository**
    ```bash
    git clone <your-repo-url>
    cd <repo-name>
    ```

2.  **Create a virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_api_key_here
    BATCH_SIZE=5
    LOG_LEVEL=INFO
    ```

5.  **Run the server**
    ```bash
    python -m app.main
    ```
    The API will be available at `http://localhost:7860`.

### 🐳 Deployment

To deploy to Google Cloud Run, simply run the deployment script:

1.  Edit `deploy.sh` and set your `PROJECT_ID` and `GEMINI_KEY`.
2.  Run the script:
    ```bash
    chmod +x deploy.sh
    ./deploy.sh
    ```

## 🔌 API Usage

**Endpoint**: `POST /extract-bill-data`

**Request Body**:
```json
{
  "url": "https://example.com/medical_bill.pdf"
}
```

**Response**:
```json
{
  "is_success": true,
  "data": {
    "pagewise_line_items": [
      {
        "page_no": "1",
        "bill_items": [
          {
            "item_name": "Paracetamol",
            "item_quantity": 2,
            "item_rate": 5.0,
            "item_amount": 10.0
          }
        ]
      }
    ],
    "total_item_count": 1
  },
  "token_usage": {
    "total_tokens": 1500,
    "input_tokens": 1000,
    "output_tokens": 500
  }
}
```

## 🛡️ Security Note

-   **API Keys**: Never commit your `.env` file or hardcode keys in `deploy.sh`. Use environment variables or Google Secret Manager for production.
-   **Input Validation**: The API validates file types and sizes to prevent abuse.

## 📄 License

[MIT License](LICENSE)
