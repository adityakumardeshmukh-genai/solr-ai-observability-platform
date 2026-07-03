#!/usr/bin/env python3
"""
response_parser.py

Parses and validates LLM responses, stripping any markdown formatting.
"""

import json
import re
from typing import Dict, Any

class ResponseParser:
    """Parses, cleans, and validates json responses from LLM completion models."""

    @staticmethod
    def parse_and_validate(raw_text: str) -> Dict[str, Any]:
        """Strips markdown markers, parses JSON, and validates SRE schema requirements."""
        cleaned = raw_text.strip()
        
        # Remove markdown fences if present
        if cleaned.startswith("```"):
            # Strip first line (e.g. ```json or ```)
            lines = cleaned.splitlines()
            if lines:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

        # Try searching for JSON block if there is extra text
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        # Parse JSON
        parsed = json.loads(cleaned)

        # Validate fields
        required_fields = ["summary", "root_cause", "business_impact", "recommendations", "priority", "confidence"]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required response field: {field}")

        # Ensure types are correct
        if not isinstance(parsed["recommendations"], list):
            parsed["recommendations"] = [str(parsed["recommendations"])]

        try:
            parsed["confidence"] = float(parsed["confidence"])
        except (TypeError, ValueError):
            parsed["confidence"] = 0.5

        return parsed
