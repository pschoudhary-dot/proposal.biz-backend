"""
Configuration settings for the Proposal Biz application.
"""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Proposal Biz"

    # hyper browser and llm keys
    HYPERBROWSER_API_KEY: str = Field(default="", env="HYPERBROWSER_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default="", env="OPENAI_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = Field(default="", env="OPENROUTER_API_KEY")

    # Docling Server Configuration
    DOCLING_SERVER_URL: str = Field(default="http://127.0.0.1:5001", env="DOCLING_SERVER_URL")
    DOCLING_ENABLED: bool = True  # Toggle for Docling integration
    DOCLING_TIMEOUT: int = 300  # 5 minutes timeout for Docling operations
    DOCLING_RETRY_ATTEMPTS: int = 3
    DOCLING_RETRY_DELAY: int = 2  # seconds
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(default="", env="SUPABASE_SERVICE_ROLE_KEY")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()