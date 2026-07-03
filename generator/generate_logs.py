#!/usr/bin/env python3
"""
generate_logs.py

Background log generator simulating a 5-node SolrCloud cluster.
Appends realistic Solr and JVM GC logs to logs/solr.log and logs/gc.log.
Supports runtime incident injections from Streamlit.
"""

import os
import time
import random
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

NODE_NAMES = ["node-1", "node-2", "node-3", "node-4", "node-5"]

SOLR_COMPONENTS = {
    "SearchHandler": [
        "Query executed in {time_ms} ms",
        "Slow query execution observed: query took {slow_time_ms} ms",
        "Search timeout occurred during shard request execution"
    ],
    "zkStateReader": [
        "Updated live nodes from ZooKeeper: status=OK"
    ],
    "ZkController": [
        "Publishing active status for leader replica on shard shard1"
    ],
    "DirectUpdateHandler2": [
        "indexing docs, count={docs}",
        "start commit{{,optimize=false,openSearcher=true,waitSearcher=true,expungeDeletes=false,softCommit={soft},prepareCommit=false}}",
    ],
    "SolrIndexSearcher": [
        "QueryResultCache hitRatio={hit_ratio:.2f}, filterCache hitRatio={filter_ratio:.2f}",
        "Opening new searcher on commit"
    ]
}

class SolrLogGenerator:
    """Simulates Solr and JVM GC logs in a background thread."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.logs_dir = self.base_dir / "logs"
        self.solr_log_path = self.logs_dir / "solr.log"
        self.gc_log_path = self.logs_dir / "gc.log"
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.status = "PAUSED"  # RUNNING, PAUSED, STOPPED
        self._thread = None
        self._lock = threading.Lock()
        
        # Keep track of GC IDs per node
        self.gc_ids = {node: 1 for node in NODE_NAMES}
        
        # Incident injection state
        self.injected_incident: Optional[str] = None
        self.injected_node: Optional[str] = None
        self.injected_step = 0
        
    def start(self):
        with self.lock():
            if self.status == "STOPPED" or self._thread is None:
                self.status = "RUNNING"
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
            elif self.status == "PAUSED":
                self.status = "RUNNING"

    def pause(self):
        with self.lock():
            if self.status == "RUNNING":
                self.status = "PAUSED"

    def stop(self):
        with self.lock():
            self.status = "STOPPED"

    def inject_scenario(self, scenario: str):
        """Schedules an incident injection in the next cycle."""
        with self.lock():
            self.injected_incident = scenario
            self.injected_node = random.choice(NODE_NAMES)
            self.injected_step = 0

    def lock(self):
        return self._lock

    def reset_files(self):
        """Clears the log files and resets state."""
        with self.lock():
            if self.solr_log_path.exists():
                self.solr_log_path.unlink()
            if self.gc_log_path.exists():
                self.gc_log_path.unlink()
            # Touch files to ensure they exist
            self.solr_log_path.touch()
            self.gc_log_path.touch()
            self.gc_ids = {node: 1 for node in NODE_NAMES}
            self.injected_incident = None
            self.injected_step = 0

    def _run_loop(self):
        while True:
            # Check status
            with self.lock():
                current_status = self.status
                if current_status == "STOPPED":
                    break
            
            if current_status == "RUNNING":
                try:
                    self._generate_cycle()
                except Exception:
                    pass
                # Append logs every 2 seconds
                time.sleep(2.0)
            else:
                time.sleep(0.5)

    def _generate_cycle(self):
        solr_lines = []
        gc_lines = []
        now = datetime.now(timezone.utc)
        
        # Load injection details
        with self.lock():
            incident = self.injected_incident
            node = self.injected_node
            step = self.injected_step

        if incident:
            # Generate logs according to the injected scenario step
            self._handle_incident_generation(incident, node, step, solr_lines, gc_lines, now)
            # Advance step
            with self.lock():
                self.injected_step += 1
        else:
            # Generate normal background noise
            self._generate_normal_noise(solr_lines, gc_lines, now)

    def _handle_incident_generation(self, incident: str, node: str, step: int, solr_lines: List[str], gc_lines: List[str], now: datetime):
        ts_solr = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        ts_gc = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        
        if incident == "Memory Leak":
            if step == 0:
                solr_lines.append(f"{ts_solr} WARN  [{node}] JVMHealthMonitor GC overhead is high. Heap usage is hovering near 1850MB\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} ERROR [{node}] JVMHealthMonitor Critical memory pressure. Full Garbage Collection running continuously.\n")
                gc_id = self._next_gc_id(node)
                gc_lines.append(f"{ts_gc} [{node}] GC({gc_id}) Pause Full (System.gc() / Allocation Failure) 1980M->1920M(2048M) 4800.0ms\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} ERROR [{node}] SolrCore java.lang.OutOfMemoryError: Java heap space\n")
                gc_lines.append(f"{ts_gc} [{node}] GC(OOM) Terminating JVM due to OutOfMemoryError\n")
            elif step == 3:
                solr_lines.append(f"{ts_solr} INFO  [{node}] CoreContainer Starting SolrCloud Node on port 8983\n")
                solr_lines.append(f"{ts_solr} INFO  [{node}] ZkController Registering node with ZooKeeper path /live_nodes\n")
            elif step == 4:
                solr_lines.append(f"{ts_solr} INFO  [{node}] RecoveryStrategy Syncing replication log with shard leader\n")
            elif step == 5:
                solr_lines.append(f"{ts_solr} INFO  [{node}] RecoveryStrategy Replication recovery completed. Node is in ACTIVE state.\n")
                self._clear_incident()

        elif incident == "ZooKeeper Failure":
            if step == 0:
                solr_lines.append(f"{ts_solr} WARN  [{node}] ZooKeeperConnection ZooKeeper client connection latency spikes to 1800ms\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} ERROR [{node}] ZkController Lost ZooKeeper connection. Stepping down as shard leader.\n")
                solr_lines.append(f"{ts_solr} ERROR [{node}] ZooKeeperConnection Connection to ZooKeeper lost. Cluster state updates suspended.\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} INFO  [{node}] ZkController Initiating leader election on shard shard1\n")
                solr_lines.append(f"{ts_solr} ERROR [{node}] SolrCore Replica is marked DOWN and unhealthy\n")
            elif step == 3:
                solr_lines.append(f"{ts_solr} INFO  [{node}] ZooKeeperConnection Successfully reconnected to ZooKeeper.\n")
                solr_lines.append(f"{ts_solr} INFO  [{node}] RecoveryStrategy Starting recovery process for replica on shard1\n")
            elif step == 4:
                solr_lines.append(f"{ts_solr} INFO  [{node}] RecoveryStrategy Recovery completed successfully. Replica active.\n")
                self._clear_incident()

        elif incident == "Disk Failure":
            if step == 0:
                solr_lines.append(f"{ts_solr} WARN  [{node}] DiskSpaceMonitor Free disk space critically low on {node} (99.5% used)\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} ERROR [{node}] DirectUpdateHandler2 Index commit failed: java.io.IOException: No space left on device\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} ERROR [{node}] RecoveryStrategy Recovery failed. Disk space check failed during replication stream.\n")
            elif step == 3:
                solr_lines.append(f"{ts_solr} INFO  [{node}] AdminCommand Admin requested directory purge and old log cleanup.\n")
            elif step == 4:
                solr_lines.append(f"{ts_solr} INFO  [{node}] RecoveryStrategy Disk space validated. Restarting recovery stream. Recovery completed.\n")
                self._clear_incident()

        elif incident == "Network Failure":
            if step == 0:
                solr_lines.append(f"{ts_solr} WARN  [{node}] SolrCmdDistributor SocketTimeoutException reading from peer nodes\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} ERROR [{node}] ZkController ZooKeeper unreachable. Client session timed out.\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} INFO  [{node}] ZkController ZooKeeper session re-established. Replicas synchronized. State is ACTIVE.\n")
                self._clear_incident()

        elif incident == "CPU Spike":
            if step == 0:
                solr_lines.append(f"{ts_solr} INFO  [{node}] DirectUpdateHandler2 High volume batch indexing request received. Processing 50,000 updates.\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} WARN  [{node}] SolrIndexWriter Segment merge triggered. CPU utilization spikes to 96%.\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} INFO  [{node}] SolrIndexWriter Segment merge finished successfully. Optimization complete.\n")
                self._clear_incident()

        elif incident == "Heap Pressure":
            if step == 0:
                solr_lines.append(f"{ts_solr} WARN  [{node}] SolrCore Heap usage is high: 1890MB / 2048MB\n")
            elif step == 1:
                gc_id = self._next_gc_id(node)
                gc_lines.append(f"{ts_gc} [{node}] GC({gc_id}) Pause Mixed (Allocation Failure) 1890M->920M(2048M) 320.0ms\n")
            elif step == 2:
                solr_lines.append(f"{ts_solr} INFO  [{node}] JVMHealthMonitor Heap usage stabilized to safe parameters.\n")
                self._clear_incident()

        elif incident == "Heavy Indexing":
            if step == 0:
                solr_lines.append(f"{ts_solr} INFO  [{node}] DirectUpdateHandler2 indexing docs, count=25000\n")
            elif step == 1:
                solr_lines.append(f"{ts_solr} INFO  [{node}] DirectUpdateHandler2 start commit{{,optimize=false,softCommit=true}}\n")
                self._clear_incident()
        else:
            self._clear_incident()

        # Write lines immediately
        self._write_lines(solr_lines, gc_lines)

    def _generate_normal_noise(self, solr_lines: List[str], gc_lines: List[str], now: datetime):
        # Generate 5-15 logs
        num_lines = random.randint(5, 15)
        for _ in range(num_lines):
            level_roll = random.random()
            if level_roll < 0.92:
                level = "INFO"
            elif level_roll < 0.99:
                level = "WARN"
            else:
                level = "ERROR"
                
            node = random.choice(NODE_NAMES)
            
            if random.random() < 0.8:
                # Solr Log
                component = random.choice(list(SOLR_COMPONENTS.keys()))
                message_template = random.choice(SOLR_COMPONENTS[component])
                params = {
                    "time_ms": random.randint(3, 40),
                    "slow_time_ms": random.randint(1001, 1500),
                    "soft": "true" if random.random() < 0.8 else "false",
                    "hit_ratio": random.uniform(0.7, 0.95),
                    "filter_ratio": random.uniform(0.8, 0.99)
                }
                try:
                    message = message_template.format(**params)
                except Exception:
                    message = message_template
                    
                if level == "WARN" and "Slow query" not in message:
                    message = f"Slight performance degradation noticed. {message}"
                elif level == "ERROR":
                    message = f"Unexpected processing error. {message}"
                    
                ts_str = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                solr_lines.append(f"{ts_str} {level:<5} [{node}] {component} {message}\n")
            else:
                # GC log
                gc_id = self._next_gc_id(node)
                before = random.randint(400, 1100)
                after = int(before * random.uniform(0.3, 0.5))
                duration = random.uniform(10.0, 45.0)
                ts_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                
                gc_lines.append(f"{ts_str} [{node}] GC({gc_id}) Pause Young (Normal) (Allocation Failure) {before}M->{after}M(2048M) {duration:.1f}ms\n")
                gc_lines.append(f"{ts_str} [{node}] GC({gc_id}) Eden: {int(before*0.4)}M->0M(600M), Survivor: {int(before*0.1)}M->{int(after*0.2)}M(100M), Old Gen: {int(before*0.5)}M->{int(after*0.8)}M(1348M)\n")

        self._write_lines(solr_lines, gc_lines)

    def _next_gc_id(self, node: str) -> int:
        gid = self.gc_ids[node]
        self.gc_ids[node] += 1
        return gid

    def _clear_incident(self):
        with self.lock():
            self.injected_incident = None
            self.injected_step = 0

    def _write_lines(self, solr_lines: List[str], gc_lines: List[str]):
        if solr_lines:
            with open(self.solr_log_path, "a") as f:
                f.writelines(solr_lines)
        if gc_lines:
            with open(self.gc_log_path, "a") as f:
                f.writelines(gc_lines)

# Singleton/shared reference in module so the generator thread runs exactly once
_generator_instance = None
_generator_lock = threading.Lock()

def get_generator(base_dir: Path) -> SolrLogGenerator:
    global _generator_instance
    with _generator_lock:
        if _generator_instance is None:
            _generator_instance = SolrLogGenerator(base_dir)
        return _generator_instance
