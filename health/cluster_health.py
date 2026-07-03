#!/usr/bin/env python3
"""
cluster_health.py

Computes health scores for individual nodes and the cluster overall based on active incidents.
"""

from typing import List, Dict, Any
from models.incident import Incident
from generator.generate_logs import NODE_NAMES

class ClusterHealthEngine:
    """Calculates node and cluster-level health metrics."""

    def compute_health(self, active_incidents: List[Incident], recent_anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates health scores and classifications for all nodes and the cluster."""
        node_scores = {node: 100 for node in NODE_NAMES}
        
        # Deductions from active incidents
        for inc in active_incidents:
            if inc.status == "Active":
                deduction = 0
                if inc.severity == "Critical":
                    deduction = 40
                elif inc.severity == "Warning":
                    deduction = 20
                else:
                    deduction = 5
                
                node_scores[inc.node] = max(0, node_scores[inc.node] - deduction)

        # Deductions from recent unresolved anomalies (last 10 minutes)
        for anomaly in recent_anomalies:
            node = anomaly.get("node")
            if node in node_scores:
                severity = anomaly.get("severity")
                deduction = 5 if severity == "Warning" else 10
                node_scores[node] = max(0, node_scores[node] - deduction)

        # Classification
        healthy_count = 0
        warning_count = 0
        critical_count = 0
        
        nodes_summary = {}
        for node, score in node_scores.items():
            if score >= 80:
                status = "Healthy"
                healthy_count += 1
            elif score >= 50:
                status = "Warning"
                warning_count += 1
            else:
                status = "Critical"
                critical_count += 1
                
            nodes_summary[node] = {
                "score": score,
                "status": status
            }

        # Overall Status
        if critical_count > 0:
            overall_status = "Critical"
        elif warning_count > 0:
            overall_status = "Warning"
        else:
            overall_status = "Healthy"

        active_count = sum(1 for inc in active_incidents if inc.status == "Active")

        return {
            "overall_status": overall_status,
            "healthy_nodes": healthy_count,
            "warning_nodes": warning_count,
            "critical_nodes": critical_count,
            "active_incidents": active_count,
            "nodes": nodes_summary
        }
