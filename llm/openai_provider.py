#!/usr/bin/env python3
"""
openai_provider.py

Azure OpenAI implementation of the BaseLLMProvider.
"""

from openai import AzureOpenAI
from llm.provider import BaseLLMProvider
from typing import Dict, Any

class AzureOpenAIProvider(BaseLLMProvider):
    """Client for Azure OpenAI API calls."""
    
    def __init__(self, config: Dict[str, Any]):
        self.endpoint = config.get("endpoint", "")
        self.api_key = config.get("api_key", "")
        self.deployment = config.get("deployment", "")
        self.api_version = config.get("api_version", "2025-01-01-preview")
        
        # Instantiate AzureOpenAI client from the official openai package
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )

    def generate_rca(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Invokes the Azure OpenAI chat completion model."""
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
