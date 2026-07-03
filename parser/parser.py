#!/usr/bin/env python3
"""
parser.py

Incremental stateful log parser for Solr and JVM GC log formats.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any

# Regular Expressions
# e.g., 2026-07-03 10:14:21.315 INFO  [node-2] SearchHandler Query executed in 24 ms
SOLR_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3})\s+([A-Z]+)\s+\[([^\]]+)\]\s+(\w+)\s+(.*)$"
)

# e.g., 2026-07-03T10:14:22.612 [node-2] GC(24) Pause Young (Normal) ...
GC_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})\s+\[([^\]]+)\]\s+GC\(\d+\)\s+(.*)$"
)

class LogParser:
    """Incrementally parses new log entries and persists state."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.storage_dir = self.base_dir / "storage"
        self.logs_dir = self.base_dir / "logs"
        
        self.solr_log_path = self.logs_dir / "solr.log"
        self.gc_log_path = self.logs_dir / "gc.log"
        self.parsed_logs_path = self.storage_dir / "parsed_logs.json"
        self.parser_state_path = self.storage_dir / "parser_state.json"
        
        # Ensure directories exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Dict[str, int]:
        """Loads byte offsets for logs."""
        if self.parser_state_path.exists():
            try:
                with open(self.parser_state_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"solr_offset": 0, "gc_offset": 0}

    def save_state(self, state: Dict[str, int]):
        """Saves current byte offsets."""
        with open(self.parser_state_path, "w") as f:
            json.dump(state, f, indent=2)

    def load_parsed_logs(self) -> List[Dict[str, Any]]:
        """Loads previously parsed logs."""
        if self.parsed_logs_path.exists():
            try:
                with open(self.parsed_logs_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_parsed_logs(self, logs: List[Dict[str, Any]]):
        """Saves parsed logs list."""
        with open(self.parsed_logs_path, "w") as f:
            json.dump(logs, f, indent=2)

    def clear_state(self):
        """Resets parsing offsets and parsed logs database."""
        self.save_state({"solr_offset": 0, "gc_offset": 0})
        self.save_parsed_logs([])

    def parse_new_entries(self) -> int:
        """Reads and parses new entries from log files. Returns number of parsed logs."""
        state = self.load_state()
        parsed_entries = []
        
        # Parse Solr Logs
        if self.solr_log_path.exists():
            current_size = self.solr_log_path.stat().st_size
            offset = state.get("solr_offset", 0)
            
            # Reset offset if file was truncated/cleared
            if offset > current_size:
                offset = 0
                
            if offset < current_size:
                with open(self.solr_log_path, "r") as f:
                    f.seek(offset)
                    lines = f.readlines()
                    state["solr_offset"] = f.tell()
                    
                for line in lines:
                    match = SOLR_LOG_RE.match(line.strip())
                    if match:
                        ts, level, node, component, message = match.groups()
                        # Convert space to 'T' for consistent ISO-8601 formatting
                        iso_ts = ts.replace(" ", "T")
                        parsed_entries.append({
                            "timestamp": iso_ts,
                            "node": node,
                            "source": "solr",
                            "level": level,
                            "component": component,
                            "message": message
                        })

        # Parse GC Logs
        if self.gc_log_path.exists():
            current_size = self.gc_log_path.stat().st_size
            offset = state.get("gc_offset", 0)
            
            if offset > current_size:
                offset = 0
                
            if offset < current_size:
                with open(self.gc_log_path, "r") as f:
                    f.seek(offset)
                    lines = f.readlines()
                    state["gc_offset"] = f.tell()
                    
                for line in lines:
                    match = GC_LOG_RE.match(line.strip())
                    if match:
                        ts, node, message = match.groups()
                        # Determine severity level for GC events
                        level = "INFO"
                        if "Full" in message or "Failure" in message:
                            level = "WARN" if "Full" in message else "INFO"
                        
                        parsed_entries.append({
                            "timestamp": ts,
                            "node": node,
                            "source": "gc",
                            "level": level,
                            "component": "GC",
                            "message": message
                        })

        if parsed_entries:
            all_logs = self.load_parsed_logs()
            all_logs.extend(parsed_entries)
            
            # Sort chronologically
            all_logs.sort(key=lambda e: e["timestamp"])
            
            # Limit database to last 5000 entries to prevent memory growth issues
            if len(all_logs) > 5000:
                all_logs = all_logs[-5000:]
                
            self.save_parsed_logs(all_logs)
            
        self.save_state(state)
        return len(parsed_entries)
