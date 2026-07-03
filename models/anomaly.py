#!/usr/bin/env python3
"""
anomaly.py

Dataclass and structures representing a detected anomaly.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any

@dataclass
class Anomaly:
    id: str
    timestamp: str      # ISO-8601 string
    node: str
    severity: str       # Critical, Warning, Info
    category: str       # Memory, Connection, Performance, Indexing, Disk, Network
    source: str         # SOLR, GC
    rule: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Anomaly":
        return cls(**data)
