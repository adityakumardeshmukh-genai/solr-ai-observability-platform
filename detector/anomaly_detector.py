#!/usr/bin/env python3
"""
anomaly_detector.py

Rule-based anomaly detector that matches parsed logs against SRE rules.
"""

import re
import uuid
from typing import List, Dict, Any
from models.anomaly import Anomaly

class AnomalyDetector:
    """Applies rules on parsed logs to detect anomalies."""
    
    def __init__(self):
        # We can compile regexes for performance
        self.latency_re = re.compile(r"Query executed in (\d+) ms")
        self.slow_latency_re = re.compile(r"Slow query execution observed: query took (\d+) ms")
        self.search_latency_re = re.compile(r"Query executed in (\d+) ms")
        
        # Regex for GC pauses: GC(24) Pause Young (Normal) (Allocation Failure) 182M->94M(2048M) 42.7ms
        self.gc_pause_re = re.compile(r"Pause\s+(\w+).*?(\d+(\.\d+)?)\s*ms")
        self.gc_heap_re = re.compile(r"(\d+)M->(\d+)M\((\d+)M\)")

    def detect(self, event: Dict[str, Any], history: List[Dict[str, Any]] = None) -> List[Anomaly]:
        """Runs rules on a single parsed log event. Returns a list of detected anomalies."""
        anomalies = []
        source = event.get("source", "").lower()
        level = event.get("level", "")
        message = event.get("message", "")
        node = event.get("node", "")
        component = event.get("component", "")
        timestamp = event.get("timestamp", "")
        
        # Unique ID generator
        def make_anomaly(severity: str, category: str, rule: str, msg: str) -> Anomaly:
            return Anomaly(
                id=f"A-{uuid.uuid4().hex[:6].upper()}",
                timestamp=timestamp,
                node=node,
                severity=severity,
                category=category,
                source=source.upper(),
                rule=rule,
                message=msg
            )

        if source == "solr":
            # 1. Replica Down
            if "marked DOWN" in message or "replica reports down" in message or "status=DOWN" in message or "reports down status" in message:
                anomalies.append(make_anomaly("Critical", "Connection", "Replica Down", message))
                
            # 2. Collection unavailable
            elif "Collection degraded" in message or "degraded status" in message or "Suspended" in message:
                anomalies.append(make_anomaly("Critical", "Connection", "Collection unavailable", message))
                
            # 3. Leader election
            elif "elect" in message.lower() or "election" in message.lower():
                anomalies.append(make_anomaly("Warning", "Connection", "Leader election", message))
                
            # 4. ZooKeeper disconnected
            elif "Lost ZooKeeper connection" in message or "ZooKeeper unreachable" in message or "session timed out" in message or "DISCONNECTED" in message:
                anomalies.append(make_anomaly("Critical", "Connection", "ZooKeeper disconnected", message))
                
            # 5. Search timeout
            elif "Search timeout" in message or "SocketTimeoutException" in message:
                anomalies.append(make_anomaly("Critical", "Performance", "Search timeout", message))
                
            # 6. Index commit failure / Disk full
            elif "Index commit failed" in message or "No space left on device" in message:
                anomalies.append(make_anomaly("Critical", "Disk", "Index commit failure", message))
                
            # 7. Recovery failure
            elif "Recovery failed" in message:
                anomalies.append(make_anomaly("Critical", "Connection", "Recovery failure", message))
                
            # 8. Node restart
            elif "Starting SolrCloud Node" in message or "starting node" in message.lower():
                anomalies.append(make_anomaly("Warning", "Connection", "Node restart", message))
                
            # 9. Query latency checks
            else:
                # Check normal/slow query times
                lat = 0
                match = self.latency_re.search(message)
                if match:
                    lat = int(match.group(1))
                else:
                    match_slow = self.slow_latency_re.search(message)
                    if match_slow:
                        lat = int(match_slow.group(1))
                        
                if lat > 3000:
                    anomalies.append(make_anomaly("Critical", "Performance", "Query latency > 3000ms", f"Query latency reached {lat}ms"))
                elif lat > 1000:
                    anomalies.append(make_anomaly("Warning", "Performance", "Query latency > 1000ms", f"Query latency reached {lat}ms"))

        elif source == "gc":
            # 1. OutOfMemoryError
            if "OutOfMemoryError" in message or "OutOfMemory" in message:
                anomalies.append(make_anomaly("Critical", "Memory", "OutOfMemoryError", message))
                
            # 2. Pause phases
            pause_match = self.gc_pause_re.search(message)
            if pause_match:
                gc_type = pause_match.group(1)
                duration_ms = float(pause_match.group(2))
                duration_s = duration_ms / 1000.0
                
                # Full GC Check
                if "Full" in gc_type:
                    if duration_s > 5.0:
                        anomalies.append(make_anomaly("Critical", "Memory", "Full GC Pause > 5 sec", f"Full GC paused for {duration_s:.1f}s"))
                    else:
                        anomalies.append(make_anomaly("Warning", "Memory", "Full GC", f"Full GC execution paused for {duration_s:.1f}s"))
                        
                    # Repeated Full GC detection using history
                    if history:
                        recent_full_gcs = [
                            h for h in history 
                            if h.get("source") == "gc" 
                            and h.get("node") == node 
                            and "Full" in h.get("message", "")
                        ]
                        # If another Full GC occurred in the last 5 minutes
                        if len(recent_full_gcs) >= 2:
                            anomalies.append(make_anomaly("Critical", "Memory", "Repeated Full GC", "Multiple Full GC cycles executed consecutively"))
                
                # Promotion Failure
                if "Promotion Failure" in message or "promotion failed" in message.lower():
                    anomalies.append(make_anomaly("Warning", "Memory", "Promotion Failure", message))
                    
                # Allocation Failure
                if "Allocation Failure" in message:
                    anomalies.append(make_anomaly("Warning", "Memory", "Allocation Failure", message))

            # 3. Heap utilization checks
            heap_match = self.gc_heap_re.search(message)
            if heap_match:
                before, after, max_heap = map(int, heap_match.groups())
                util = (before / max_heap) * 100.0
                
                if util > 95.0:
                    anomalies.append(make_anomaly("Critical", "Memory", "Heap Usage > 95%", f"Heap utilization reached {util:.1f}% ({before}M / {max_heap}M)"))
                elif util > 85.0:
                    anomalies.append(make_anomaly("Warning", "Memory", "Heap Usage > 85%", f"Heap utilization reached {util:.1f}% ({before}M / {max_heap}M)"))

        return anomalies
