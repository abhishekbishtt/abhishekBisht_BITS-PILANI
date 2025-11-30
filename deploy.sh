#!/bin/bash

# Quick Deploy Script for Google Cloud Run
# No artificial remote‑call limit – we rely on Cloud Run timeout (30 min) for large PDFs

# 1) CONFIGURE THESE
PROJECT_ID="medical-bill-extract-v1"          # <-- replace with your actual project ID
REGION="us-central1"
SERVICE_NAME="medical-bill-extraction-api"  # keep same as your service
GEMINI_KEY="AIzaSyDm06BVRuFXK4E__w-UR-b1St57Yk6Gpzc"       # <-- replace with your real Gemini key

echo "🚀 Deploying $SERVICE_NAME to Google Cloud Run in project $PROJECT_ID ($REGION)"
echo ""

# 2) Set project
echo "📝 Setting project..."
gcloud config set project "$PROJECT_ID"

# 3) Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# 4) Deploy from source using your Dockerfile
echo "🐳 Building and deploying..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="$GEMINI_KEY" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 1800 \
  --max-instances 10 \
  --port 8080

echo ""
echo "✅ Deployment complete!"
echo "👉 Get the service URL with:"
echo "   gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'"
