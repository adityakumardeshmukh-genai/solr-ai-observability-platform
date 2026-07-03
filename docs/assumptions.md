# System Assumptions

## Table of Contents
1. [Overview](#1-overview)
2. [List of Assumptions](#2-list-of-assumptions)

---

## 1. Overview
This document registers the operational, infrastructural, and formatting assumptions applied during the design and development of the platform.

---

## 2. List of Assumptions
1. **Clock Synchronization**: All nodes use Network Time Protocol (NTP) to synchronize system clocks. Timestamps are assumed to be aligned.
2. **Log Formatting Consistency**: Solr logs adhere strictly to standard log4j patterns.
3. **GC Log Engine**: JVM garbage collection logs follow the standard G1GC unified logging format (`-Xlog:gc*`).
4. **Single-threaded Parser Access**: Only one parser instance executes writes to `parsed_logs.json` at any given time, preventing write collisions.
5. **Negligible Clock Drift**: Time drift between nodes is smaller than the 5-second simulation ticks.
6. **Unique Hostnames**: Node identifiers (`node-1` to `node-5`) are unique within the network.
7. **Chronological Writes**: Logs are appended to log files sequentially by timestamp. Out-of-order log insertions do not occur.
8. **Line Integrity**: Log messages are written in a single flush. Partially written or interleaved log lines are not encountered.
9. **Universal Time Zone**: The platform parses all times as UTC, avoiding offsets and local DST adjustments.
10. **Static Shard Configuration**: Shard layout (`shard1` containing active replicas) remains unchanged throughout the simulation.
11. **Standalone ZooKeeper**: ZooKeeper runs as an independent cluster; failures are simulated on Solr connection states, not on physical ZK nodes.
12. **Advisory AI Role**: AI RCA reports are advisory. Critical recovery tasks require manual SRE execution or verification.
13. **Local File Permissions**: The application context has read/write permissions to the `logs/` and `storage/` directories.
14. **Persistent Environment**: Session variables remain stable between Streamlit refresh triggers.
15. **Symmetric Network Latency**: Network round-trip delays between nodes are uniform unless failure scenarios are explicitly injected.
16. **Immutable Limits**: Maximum JVM heap allocation is fixed at `2048M` per node.
17. **OOM JVM Termination**: OutOfMemory errors crash the running JVM, requiring a restart sequence.
18. **Uncorrupted Logs**: Log files do not undergo manual external edits during pipeline execution.
19. **Sequential Injections**: Only one failure scenario is injected at a time to prevent overlapping state anomalies.
20. **Active User Session**: Streamlit runs inside a single-user browser session. Multiple concurrent client sessions do not conflict.
