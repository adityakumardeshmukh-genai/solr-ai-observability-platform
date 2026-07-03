#!/usr/bin/env python3
"""
settings.py

Loads and manages environment variables and dashboard overrides for LLM settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    """Provides configuration parameters for LLM providers."""
    
    @staticmethod
    def get_provider() -> str:
        return os.getenv("LLM_PROVIDER", "gemini").lower()
        
    @staticmethod
    def get_azure_config() -> dict:
        return {
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
        }

    @staticmethod
    def get_gemini_config() -> dict:
        return {
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        }

    @staticmethod
    def get_inference_params() -> dict:
        try:
            temp = float(os.getenv("TEMPERATURE", "0"))
        except ValueError:
            temp = 0.0
            
        try:
            tokens = int(os.getenv("MAX_TOKENS", "1200"))
        except ValueError:
            tokens = 1200
            
        return {
            "temperature": temp,
            "max_tokens": tokens
        }
