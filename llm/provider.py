#!/usr/bin/env python3
"""
provider.py

Defines the common interface for LLM providers and the factory to instantiate them.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseLLMProvider(ABC):
    """Abstract interface that all LLM client implementations must follow."""
    
    @abstractmethod
    def generate_rca(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Invokes the model to generate the root cause analysis using the compiled prompt."""
        pass

class LLMProviderFactory:
    """Factory to instantiate the configured LLM provider."""

    @staticmethod
    def create(provider_name: str, config: Dict[str, Any]) -> BaseLLMProvider:
        """Instantiates the correct provider class."""
        name = provider_name.lower().strip()
        if name == "azure":
            from llm.openai_provider import AzureOpenAIProvider
            return AzureOpenAIProvider(config)
        elif name == "gemini":
            from llm.gemini_provider import GeminiProvider
            return GeminiProvider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
