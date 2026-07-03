#!/usr/bin/env python3
"""
correlation_engine.py

Groups individual anomalies into correlated incidents based on node, category, and time windows.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from models.anomaly import Anomaly
from models.incident import Incident

class CorrelationEngine:
    """Correlates anomalies into high-level incidents."""
    
    def __init__(self, time_window_seconds: float = 300.0):
        self.time_window_seconds = time_window_seconds

    def correlate(self, anomalies: List[Anomaly], existing_incidents: List[Incident]) -> List[Incident]:
        """Correlates new anomalies into active incidents, updating them or creating new ones."""
        incidents_dict = {inc.id: inc for inc in existing_incidents}
        
        for anomaly in anomalies:
            # Try to find a matching active incident
            matched_incident: Optional[Incident] = None
            anomaly_time = datetime.fromisoformat(anomaly.timestamp.replace("Z", "+00:00"))
            
            for inc in incidents_dict.values():
                if inc.status == "Active" and inc.node == anomaly.node and inc.category == anomaly.category:
                    # Check window
                    inc_last_time = datetime.fromisoformat(inc.last_update.replace("Z", "+00:00"))
                    diff = abs((anomaly_time - inc_last_time).total_seconds())
                    if diff <= self.time_window_seconds:
                        matched_incident = inc
                        break
            
            if matched_incident:
                # Update existing incident
                matched_incident.anomaly_ids.append(anomaly.id)
                matched_incident.num_anomalies += 1
                matched_incident.last_update = anomaly.timestamp
                
                # Update duration
                start_time = datetime.fromisoformat(matched_incident.start_time.replace("Z", "+00:00"))
                matched_incident.duration = (anomaly_time - start_time).total_seconds()
                
                # Elevate severity if needed
                if anomaly.severity == "Critical":
                    matched_incident.severity = "Critical"
                    
                # Append to timeline
                matched_incident.timeline.append({
                    "timestamp": anomaly.timestamp,
                    "message": f"[{anomaly.severity}] {anomaly.rule}: {anomaly.message}"
                })
            else:
                # Create a new incident
                inc_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
                new_inc = Incident(
                    id=inc_id,
                    start_time=anomaly.timestamp,
                    last_update=anomaly.timestamp,
                    duration=0.0,
                    node=anomaly.node,
                    severity=anomaly.severity,
                    category=anomaly.category,
                    status="Active",
                    timeline=[{
                        "timestamp": anomaly.timestamp,
                        "message": f"[{anomaly.severity}] {anomaly.rule}: {anomaly.message}"
                    }],
                    num_anomalies=1,
                    anomaly_ids=[anomaly.id]
                )
                incidents_dict[inc_id] = new_inc
                
        # Resolve incidents if a recovery log is parsed, or if they have timed out.
        # However, to be simple and robust: we can check if they haven't seen updates for e.g. 5 minutes.
        # But wait, since we are doing this live, we will let the EventProcessor handle resolution
        # based on recovery logs or timeout.
        return list(incidents_dict.values())

    def check_resolutions(self, incidents: List[Incident], parsed_logs: List[Dict[str, Any]]) -> List[Incident]:
        """Looks at recovery events to resolve incidents."""
        # Find all recovery/stability logs
        recovery_events = [
            log for log in parsed_logs
            if "recovery completed successfully" in log.get("message", "").lower()
            or "stabilized" in log.get("message", "").lower()
            or "reconnected to zookeeper" in log.get("message", "").lower()
            or "recovery completed" in log.get("message", "").lower()
            or "optimization complete" in log.get("message", "").lower()
        ]
        
        for inc in incidents:
            if inc.status == "Active":
                # Check for matching recovery log on the same node after the start_time
                inc_start = datetime.fromisoformat(inc.start_time.replace("Z", "+00:00"))
                for rev in recovery_events:
                    if rev.get("node") == inc.node:
                        rev_time = datetime.fromisoformat(rev["timestamp"].replace("Z", "+00:00"))
                        if rev_time > inc_start:
                            inc.status = "Resolved"
                            inc.timeline.append({
                                "timestamp": rev["timestamp"],
                                "message": f"[Info] Recovery event detected: {rev['message']}"
                            })
                            # Update duration
                            inc.duration = (rev_time - inc_start).total_seconds()
                            inc.last_update = rev["timestamp"]
                            break
                            
        return incidents
