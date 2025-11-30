from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application Settings
    APP_NAME: str = "Medical Bill Extraction API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 7860))
    
    # Gemini Configuration - ADD GOOGLE_API_KEY
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")  # ADD THIS LINE
    GEMINI_MODEL: str = "gemini-2.0-flash-001"
    GEMINI_TEMPERATURE: float = 0.1
    
    # Document Processing Settings
    MAX_FILE_SIZE_MB: int = 500
    MAX_PAGES: int = 500
    PDF_DPI: int = 300
    TIMEOUT_SECONDS: int = 300
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
