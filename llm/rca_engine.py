#!/usr/bin/env python3
"""
rca_engine.py

Orchestrates caching, prompt compilation, provider execution, retries, and JSON database updates.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from config.settings import Settings
from llm.provider import LLMProviderFactory
from llm.prompt_builder import PromptBuilder
from llm.response_parser import ResponseParser

logger = logging.getLogger(__name__)

class RCAEngine:
    """Orchestrates AI Root Cause Analysis pipeline."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.storage_dir = self.base_dir / "storage"
        self.prompts_dir = self.base_dir / "prompts"
        self.cache_path = self.storage_dir / "ai_analysis.json"
        self.prompt_builder = PromptBuilder(self.prompts_dir / "rca_prompt.txt")
        
        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def load_cache(self) -> Dict[str, Any]:
        """Loads cached analyses."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_cache(self, cache: Dict[str, Any]):
        """Saves analyses to the local JSON file."""
        with open(self.cache_path, "w") as f:
            json.dump(cache, f, indent=2)

    def clear_cache(self):
        """Clears cached SRE results."""
        self.save_cache({})

    def analyze_incident(
        self, 
        incident: Dict[str, Any], 
        cluster_health: str = "Healthy",
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temp_override: Optional[float] = None,
        tokens_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """Runs the LLM analysis with cache checks, prompt building, and retry validation."""
        incident_id = incident.get("id", "UNKNOWN")
        cache = self.load_cache()

        # 1. Return cached SRE if exists
        if incident_id in cache:
            return cache[incident_id]

        # 2. Compile SRE Prompt
        try:
            prompt = self.prompt_builder.build_prompt(incident, cluster_health)
        except Exception as e:
            logger.error(f"Prompt compilation failed: {e}")
            return self._fallback_response(f"Prompt generation error: {str(e)}")

        # 3. Retrieve Config and Overrides
        provider_name = provider_override or Settings.get_provider()
        
        # Load API parameters
        if provider_name == "azure":
            config = Settings.get_azure_config()
            if model_override:
                config["deployment"] = model_override
        else:
            config = Settings.get_gemini_config()
            if model_override:
                config["model"] = model_override
                
        # Fallback values
        params = Settings.get_inference_params()
        temperature = temp_override if temp_override is not None else params["temperature"]
        max_tokens = tokens_override if tokens_override is not None else params["max_tokens"]

        # If API keys are missing, return early with clear instructions rather than crash
        api_key = config.get("api_key", "")
        if not api_key:
            return self._fallback_response(f"API key for provider {provider_name} is missing. Please set it in your environment or .env file.")

        # 4. Instantiate Client and Run with Retry
        tries = 2
        last_error = ""
        
        for attempt in range(tries):
            try:
                # Instantiate client
                client = LLMProviderFactory.create(provider_name, config)
                raw_completion = client.generate_rca(prompt, temperature, max_tokens)
                
                # Parse and validate response schema
                analysis = ResponseParser.parse_and_validate(raw_completion)
                
                # Store back in cache
                cache[incident_id] = analysis
                self.save_cache(cache)
                return analysis
            except Exception as ex:
                last_error = str(ex)
                logger.warning(f"RCA generation attempt {attempt + 1} failed: {ex}")
                
        # Return fallback on failure
        return self._fallback_response(f"AI Analysis Unavailable. Error: {last_error}")

    def _fallback_response(self, detail: str) -> Dict[str, Any]:
        return {
            "summary": "AI Analysis Unavailable",
            "root_cause": detail,
            "business_impact": "Analysis could not be generated. Please check SRE credentials and parameters.",
            "recommendations": [
                "Verify LLM Provider selection in sidebar",
                "Ensure API Key is correct and has quota",
                "Check connectivity to model endpoints"
            ],
            "priority": "High",
            "confidence": 0.0
        }
