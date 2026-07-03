#!/usr/bin/env python3
"""
gemini_provider.py

Google Gemini API implementation of the BaseLLMProvider.
"""

import google.generativeai as genai
from llm.provider import BaseLLMProvider
from typing import Dict, Any

class GeminiProvider(BaseLLMProvider):
    """Client for Google Gemini Developer API."""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model", "gemini-2.5-flash")
        
        # Configure the official Google GenerativeAI package
        genai.configure(api_key=self.api_key)

    def generate_rca(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Invokes the Google Gemini model."""
        model = genai.GenerativeModel(self.model_name)
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
