"""
Configuration settings for the Proposal Biz application.
"""
from typing import Optional, Dict, Any
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
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = Field(..., env="OPENROUTER_API_KEY")
    
    # Langfuse Configuration
    LANGFUSE_SECRET_KEY: str = Field(..., env="LANGFUSE_SECRET_KEY")
    LANGFUSE_PUBLIC_KEY: str = Field(..., env="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_HOST: str = Field("https://cloud.langfuse.com", env="LANGFUSE_HOST")

    # Storage Configuration
    STORAGE_BUCKET_NAME: str = Field("websiteassets", env="STORAGE_BUCKET_NAME")
    
    # OpenRouter Models Configuration
    OPENROUTER_MODELS: Dict[str, Dict[str, Any]] = {
        "gemini-2.0-flash-exp": {
            "id": "google/gemini-2.0-flash-exp:free",
            "context_limit": 1_000_000,
            "type": "free",
            "description": "Google Gemini 2.0 Flash Exp - 1M context"
        },
        "gemini-2.5-pro-preview": {
            "id": "google/gemini-2.5-pro-preview",
            "context_limit": 1_048_576,
            "type": "paid",
            "description": "Google Gemini 2.5 Pro Preview - 1M+ context"
        },
        "deepseek-r1": {
            "id": "deepseek/deepseek-r1-0528:free",
            "context_limit": 164_000,
            "type": "free",
            "description": "DeepSeek R1 - 164K context"
        }
    }
    
    # Default model for content library processing
    DEFAULT_CONTENT_LIB_MODEL: str = "gemini-2.0-flash-exp"
    
    # Token estimation multiplier (rough estimate: 1 char ≈ 0.25 tokens for most models)
    CHARS_PER_TOKEN_ESTIMATE: float = 4.0

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()