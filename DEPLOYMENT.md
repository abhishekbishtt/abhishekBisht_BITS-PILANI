# Google Cloud Run Deployment Guide

## Prerequisites
- Google account (you already have one for Gemini API)
- Credit card for $300 free trial signup (won't be charged during trial)

---

## Step 1: Install Google Cloud CLI

### For macOS:
```bash
# Install using Homebrew
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### Initialize gcloud:
```bash
# Login to your Google account
gcloud auth login

# Set your project (we'll create one in next step)
gcloud config set project YOUR_PROJECT_ID
```

---

## Step 2: Create Google Cloud Project

1. Go to: https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name it: `medical-bill-api` (or any name)
4. Note your **Project ID** (e.g., `medical-bill-api-123456`)
5. Enable billing (activate $300 free trial)

### Enable required APIs:
```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com
```

---

## Step 3: Configure Environment Variables

Create a `.env.yaml` file for Cloud Run secrets:

```bash
# In your project root
cat > .env.yaml << EOF
GEMINI_API_KEY: "YOUR_GEMINI_API_KEY_HERE"
EOF
```

**IMPORTANT:** Replace `YOUR_GEMINI_API_KEY_HERE` with your actual Gemini API key!

---

## Step 4: Deploy to Cloud Run

### One-command deployment:
```bash
gcloud run deploy medical-bill-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10
```

**What this does:**
- `--source .` → Builds from current directory (automatic Docker build)
- `--region us-central1` → Deploy to US Central (close to Google APIs)
- `--allow-unauthenticated` → Public access (for hackathon demo)
- `--env-vars-file` → Sets GEMINI_API_KEY securely
- `--memory 2Gi` → Sufficient RAM for PDF processing
- `--timeout 300` → 5min timeout (default is 60s, too low)
- `--max-instances 10` → Auto-scale up to 10 instances

### Deployment takes ~3-5 minutes

---

## Step 5: Get Your URL

After deployment, you'll see:
```
Service URL: https://medical-bill-api-XXXXXX-uc.a.run.app
```

**Copy this URL!** This is your public API endpoint.

---

## Step 6: Test Your Deployment

```bash
# Test the health endpoint
curl https://YOUR-SERVICE-URL.run.app/health

# Test extraction (replace with your URL and document)
curl -X POST https://YOUR-SERVICE-URL.run.app/extract-bill-data \
  -H "Content-Type: application/json" \
  -d '{"document": "http://example.com/sample.pdf"}'
```

---

## Quick Commands Reference

```bash
# View logs
gcloud run services logs read medical-bill-api --region us-central1

# Update service (after code changes)
gcloud run deploy medical-bill-api --source . --region us-central1

# Delete service (to save credits)
gcloud run services delete medical-bill-api --region us-central1

# Check costs
gcloud billing projects describe YOUR_PROJECT_ID
```

---

## Alternative: Quick Deploy Script

Save this as `deploy.sh`:

```bash
#!/bin/bash

# Replace with your actual values
PROJECT_ID="medical-bill-api-123456"
REGION="us-central1"
SERVICE_NAME="medical-bill-api"

# Set project
gcloud config set project $PROJECT_ID

# Deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10

echo "Deployment complete!"
echo "Your API URL will be shown above ⬆️"
```

Then run:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Troubleshooting

### "Permission denied" error
```bash
gcloud auth login
gcloud auth application-default login
```

### "API not enabled" error
```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### "Build failed" error
- Check that `Dockerfile` exists in project root
- Ensure all files in `requirements.txt` are installable

### Deployment hangs
- Wait 5 minutes (first build takes time)
- Check logs: `gcloud builds list`

---

## Cost Estimate (Free Tier)

**Your usage for hackathon:**
- ~100 requests during demo = **FREE** (well within $300 credit)
- Cloud Run free tier: 2 million requests/month
- You'll use < 0.01% of your free trial

---

## Next Steps After Deployment

1. Update your frontend/demo to use the new Cloud Run URL
2. Test with a few sample bills
3. Show to hackathon judges! 🎉

**Pro tip:** Add the `/docs` endpoint to your demo to show the auto-generated API documentation!
