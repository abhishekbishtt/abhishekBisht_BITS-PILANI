from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.api.routes import extraction

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Extract line items from medical bills using AI",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(extraction.router, tags=["Extraction"])

@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Medical Bill Extraction API",
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
