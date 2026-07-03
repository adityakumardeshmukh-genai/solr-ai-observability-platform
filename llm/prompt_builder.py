#!/usr/bin/env python3
"""
prompt_builder.py

Reads and compiles the SRE system prompt template.
"""

from pathlib import Path
from typing import Dict, Any

class PromptBuilder:
    """Helper class to load SRE prompts and inject runtime incident context."""

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def build_prompt(self, incident: Dict[str, Any], cluster_health: str = "Healthy") -> str:
        """Reads prompts/rca_prompt.txt and injects incident data variables."""
        if not self.prompt_path.exists():
            raise FileNotFoundError(f"System prompt template not found at: {self.prompt_path}")

        with open(self.prompt_path, "r") as f:
            template = f.read()

        # Format timeline as a list of strings
        raw_timeline = incident.get("timeline", [])
        timeline_str = ""
        for event in raw_timeline:
            # timeline events can be dicts or strings
            if isinstance(event, dict):
                t = event.get("timestamp", "")
                m = event.get("message", "")
                timeline_str += f"- [{t}] {m}\n"
            else:
                timeline_str += f"- {event}\n"

        # Format parameters safely
        params = {
            "incident_id": incident.get("id", "INC-UNKNOWN"),
            "node": incident.get("node", "Unknown"),
            "severity": incident.get("severity", "Info"),
            "category": incident.get("category", "General"),
            "cluster_health": cluster_health,
            "duration": str(incident.get("duration", 0.0)),
            "num_anomalies": str(incident.get("num_anomalies", 0)),
            "timeline": timeline_str.strip()
        }

        return template.format(**params)
