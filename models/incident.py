#!/usr/bin/env python3
"""
incident.py

Dataclass and structures representing a correlated incident.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

@dataclass
class Incident:
    id: str
    start_time: str      # ISO-8601
    last_update: str     # ISO-8601
    duration: float      # in seconds
    node: str
    severity: str        # Critical, Warning, Info
    category: str
    status: str          # Active, Resolved
    timeline: List[Dict[str, Any]] = field(default_factory=list) # [{timestamp, message}]
    num_anomalies: int = 0
    anomaly_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Incident":
        return cls(**data)
