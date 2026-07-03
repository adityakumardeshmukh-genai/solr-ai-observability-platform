#!/usr/bin/env python3
"""
event_processor.py

Central processing pipeline coordinating parser -> detector -> correlation -> health.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from parser.parser import LogParser
from detector.anomaly_detector import AnomalyDetector
from correlation.correlation_engine import CorrelationEngine
from health.cluster_health import ClusterHealthEngine
from models.anomaly import Anomaly
from models.incident import Incident

class EventProcessor:
    """Coordinates log processing, anomaly detection, incident correlation, and health analysis."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.storage_dir = self.base_dir / "storage"
        self.parser = LogParser(self.base_dir)
        self.detector = AnomalyDetector()
        self.correlator = CorrelationEngine()
        self.health_engine = ClusterHealthEngine()

        self.anomalies_path = self.storage_dir / "anomalies.json"
        self.incidents_path = self.storage_dir / "incidents.json"
        self.health_path = self.storage_dir / "cluster_health.json"

    def load_anomalies(self) -> List[Dict[str, Any]]:
        if self.anomalies_path.exists():
            try:
                with open(self.anomalies_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_anomalies(self, anomalies: List[Dict[str, Any]]):
        with open(self.anomalies_path, "w") as f:
            json.dump(anomalies, f, indent=2)

    def load_incidents(self) -> List[Incident]:
        if self.incidents_path.exists():
            try:
                with open(self.incidents_path, "r") as f:
                    data = json.load(f)
                    return [Incident.from_dict(d) for d in data]
            except Exception:
                pass
        return []

    def save_incidents(self, incidents: List[Incident]):
        data = [inc.to_dict() for inc in incidents]
        with open(self.incidents_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_health(self) -> Dict[str, Any]:
        if self.health_path.exists():
            try:
                with open(self.health_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_health(self, health: Dict[str, Any]):
        with open(self.health_path, "w") as f:
            json.dump(health, f, indent=2)

    def clear_state(self):
        """Clears anomalies, incidents, and health storage."""
        self.save_anomalies([])
        self.save_incidents([])
        self.save_health({})

    def process(self) -> Dict[str, Any]:
        """Main pipeline execution."""
        # 1. Trigger parser to scan for new entries
        self.parser.parse_new_entries()
        
        # Load parser state to check last evaluated log count
        parser_state = self.parser.load_state()
        evaluated_count = parser_state.get("evaluated_count", 0)
        
        # Load logs
        all_logs = self.parser.load_parsed_logs()
        total_logs_count = len(all_logs)
        
        # Get only new logs
        new_logs = all_logs[evaluated_count:]
        
        # Load existing database
        anomalies_db = self.load_anomalies()
        incidents_db = self.load_incidents()
        
        new_anomalies_objects: List[Anomaly] = []
        
        # 2. Run Anomaly Detector
        for i, event in enumerate(new_logs):
            history_slice = all_logs[:evaluated_count + i]
            detected = self.detector.detect(event, history=history_slice)
            new_anomalies_objects.extend(detected)
            
        # Convert new anomalies to dicts and append
        if new_anomalies_objects:
            new_anomalies_dicts = [a.to_dict() for a in new_anomalies_objects]
            anomalies_db.extend(new_anomalies_dicts)
            self.save_anomalies(anomalies_db)
            
        # Update evaluation progress
        parser_state["evaluated_count"] = total_logs_count
        self.parser.save_state(parser_state)
        
        # 3. Run Correlator
        if new_anomalies_objects:
            incidents_db = self.correlator.correlate(new_anomalies_objects, incidents_db)
            
        # Run resolution check on all active incidents using history
        incidents_db = self.correlator.check_resolutions(incidents_db, all_logs)
        self.save_incidents(incidents_db)
        
        # 4. Compute Health
        active_incidents = [inc for inc in incidents_db if inc.status == "Active"]
        recent_anomalies = anomalies_db[-30:]  # Grab last 30 for recent pressure checks
        health_data = self.health_engine.compute_health(active_incidents, recent_anomalies)
        self.save_health(health_data)
        
        return health_data
