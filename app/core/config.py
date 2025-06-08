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

    HYPERBROWSER_API_KEY: str = Field(..., env="HYPERBROWSER_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    APIFY_API_TOKEN: Optional[str] = Field(None, env="APIFY_API_TOKEN")
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = Field(None, env="SUPABASE_SERVICE_ROLE_KEY")
    OPENROUTER_API_KEY: str = Field(..., env="OPENROUTER_API_KEY")

    # Storage Configuration
    STORAGE_BUCKET_NAME: str = Field("websiteassets", env="STORAGE_BUCKET_NAME")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()