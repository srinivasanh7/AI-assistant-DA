"""Application configuration and settings."""

import os
from typing import Optional

from dotenv import load_dotenv
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    app_title: str = Field(default="AI-Powered Logistics Assistant (Phase 1)", env="APP_TITLE")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # LLM Provider Configuration
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")  # "openai" or "gemini"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.0, env="OPENAI_TEMPERATURE")
    
    # Gemini Configuration
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.0, env="GEMINI_TEMPERATURE")
    
    # Data Processing Configuration
    numeric_threshold: float = Field(default=0.8, env="NUMERIC_THRESHOLD")
    datetime_threshold: float = Field(default=0.7, env="DATETIME_THRESHOLD")
    categorical_threshold: int = Field(default=50, env="CATEGORICAL_THRESHOLD")
    
    # File Paths
    datasets_dir: str = Field(default="datasets", env="DATASETS_DIR")
    metadata_dir: str = Field(default="metadata", env="METADATA_DIR")
    
    # Data Sampling
    max_categorical_unique: int = Field(default=50, env="MAX_CATEGORICAL_UNIQUE")
    data_sample_size: int = Field(default=15, env="DATA_SAMPLE_SIZE")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_openai_key(self) -> None:
        """Validate that OpenAI API key is set."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set it in your environment or .env file."
            )
    
    def validate_gemini_key(self) -> None:
        """Validate that Gemini API key is set."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or .env file."
            )
    
    def validate_current_provider_key(self) -> None:
        """Validate that the current provider's API key is set."""
        if self.llm_provider == "gemini":
            self.validate_gemini_key()
        else:  # Default to OpenAI
            self.validate_openai_key()


# Global settings instance (lazy)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings with lazy initialization."""
    global _settings
    if _settings is None:
        print("Initializing Settings (lazy)...")
        _settings = Settings()
    return _settings
