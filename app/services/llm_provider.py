"""LLM Provider abstraction layer for switching between OpenAI and Gemini."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from ..config.settings import get_settings


class LLMProviderType(Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    GEMINI = "gemini"


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, settings=None):
        """Initialize the provider."""
        self.settings = settings or get_settings()
    
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """Get the LLM instance."""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> None:
        """Validate that the API key is set."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""
    
    def validate_api_key(self) -> None:
        """Validate that OpenAI API key is set."""
        if not self.settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set it in your environment or .env file."
            )
    
    def get_llm(self) -> ChatOpenAI:
        """Get configured OpenAI LLM instance."""
        return ChatOpenAI(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            api_key=self.settings.openai_api_key,
            request_timeout=60,
            max_retries=2
        )


class GeminiProvider(BaseLLMProvider):
    """Gemini provider implementation."""
    
    def validate_api_key(self) -> None:
        """Validate that Gemini API key is set."""
        if not self.settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please set it in your environment or .env file."
            )
    
    def get_llm(self) -> ChatGoogleGenerativeAI:
        """Get configured Gemini LLM instance."""
        return ChatGoogleGenerativeAI(
            model=self.settings.gemini_model,
            temperature=self.settings.gemini_temperature,
            google_api_key=self.settings.gemini_api_key,
            timeout=60
        )


class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    _providers = {
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.GEMINI: GeminiProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_type: LLMProviderType, settings=None) -> BaseLLMProvider:
        """Create an LLM provider instance."""
        if provider_type not in cls._providers:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        provider_class = cls._providers[provider_type]
        return provider_class(settings)
    
    @classmethod
    def get_configured_provider(cls, settings=None) -> BaseLLMProvider:
        """Get the provider based on configuration."""
        settings = settings or get_settings()

        # Determine which provider to use based on configuration
        if settings.llm_provider == LLMProviderType.GEMINI.value:
            print(f"🤖 Using LLM Provider: GEMINI")
            return cls.create_provider(LLMProviderType.GEMINI, settings)
        else:
            # Default to OpenAI
            print(f"🤖 Using LLM Provider: OPENAI")
            return cls.create_provider(LLMProviderType.OPENAI, settings)


# Convenience function for getting configured LLM
def get_configured_llm(settings=None) -> BaseChatModel:
    """Get a configured LLM instance based on current settings."""
    provider = LLMProviderFactory.get_configured_provider(settings)
    provider.validate_api_key()
    return provider.get_llm()