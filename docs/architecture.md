# System Architecture Document

## Table of Contents
1. [Overview](#1-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Descriptions](#3-component-descriptions)
4. [Data Flow](#4-data-flow)
5. [Technology Choices](#5-technology-choices)
6. [Design Decisions](#6-design-decisions)
7. [Scalability Considerations](#7-scalability-considerations)
8. [Security Considerations](#8-security-considerations)
9. [Production Deployment Considerations](#9-production-deployment-considerations)
10. [Observability Considerations](#10-observability-considerations)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Overview
The **AI Powered Solr Observability Platform** is a real-time, stateful log simulation, anomaly detection, incident correlation, and AI-driven Root Cause Analysis (RCA) platform designed to monitor distributed Apache SolrCloud deployments. It decouples high-volume raw telemetry processing from expensive generative AI inferences by applying deterministic SRE rules to correlate logs into isolated incidents before querying Large Language Models.

---

## 2. High-Level Architecture

### ASCII Diagram
```text
  +-----------------------------------------------------------------------+
  |                             LOG GENERATOR                             |
  |  (Simulates 5-Node SolrCloud Cluster, background thread, heartbeats)  |
  +-----------------------------------+-----------------------------------+
                                      | Writes to log files
                                      v
  +-----------------------------------------------------------------------+
  |                              LOG FILES                                |
  |               (logs/solr.log)            (logs/gc.log)                |
  +-----------------------------------+-----------------------------------+
                                      | Read incrementally via byte offsets
                                      v
  +-----------------------------------------------------------------------+
  |                         EVENT PROCESSOR PIPELINE                      |
  |                                                                       |
  |  +--------------------+   +-------------------+   +----------------+  |
  |  |     Log Parser     |-->|  Anomaly Detector |-->|  Correlator    |  |
  |  | (Incremental Regex)|   | (SRE Rules Engine)|   | (Time-Window)  |  |
  |  +--------------------+   +-------------------+   +--------+-------+  |
  |                                                            |          |
  |                                                            v          |
  |  +---------------------------------------------------------+-------+  |
  |  |                         Cluster Health Engine                      |  |
  |  |              (Node & Cluster level status calculation)             |  |
  |  +-----------------------------------------------------------------+  |
  +-----------------------------------+-----------------------------------+
                                      | Persists JSON files
                                      v
  +-----------------------------------------------------------------------+
  |                            STORAGE ENGINE                             |
  |      (parsed_logs.json, anomalies.json, incidents.json, health.json)  |
  +-----------------------------------+-----------------------------------+
                                      | Loads state for visualization
                                      v
  +-----------------------------------------------------------------------+
  |                          STREAMLIT DASHBOARD                          |
  |  - Active Incidents Panel                                             |
  |  - Detected Anomalies Table                                           |
  |  - Node Status Health Scores                                          |
  |  - Failure Injections Dropdown & AI Settings                          |
  +-----------------------------------+-----------------------------------+
                                      | Trigger Explain with AI (Manual/Auto)
                                      v
  +-----------------------------------------------------------------------+
  |                         AI RCA ENGINE SERVICE                         |
  |   - Caching (ai_analysis.json)                                        |
  |   - Prompt Builder (rca_prompt.txt)                                   |
  |   - Response Parser & Format Validator                                |
  +---------------------------------+-------------------------------------+
                                    |
            +-----------------------+-----------------------+
            | API Request                                   | API Request
            v                                               v
  +-----------------------------------+           +-----------------------+
  |        GOOGLE GEMINI API          |           |   AZURE OPENAI API    |
  |        (gemini-2.0-flash)         |           |       (gpt-4o)        |
  +-----------------------------------+           +-----------------------+
```

```text
[ Replace with Draw.io Diagram ]
```

---

## 3. Component Descriptions

### 3.1 Log Generator
A background thread simulating normal operations and manual failure injections for a 5-node cluster (`node-1` to `node-5`). It writes directly to `logs/solr.log` and `logs/gc.log` using synchronized UTC timestamps.

### 3.2 Log Parser
Maintains incremental parsing progress via byte offset tracking stored in `storage/parser_state.json`. Employs optimized regular expressions to ingest and convert raw Solr and G1GC log strings into structured JSON.

### 3.3 Anomaly Detector
A deterministic rules engine executing static SRE pattern matching (e.g. latency checks, out of memory events, replication failures) to emit standardized `Anomaly` dataclass objects.

### 3.4 Correlation Engine
A time-windowed aggregator that binds related anomalies occurring on the same node within a 5-minute sliding window into a unified `Incident`. It updates incident duration, elevates severities, compiles timelines, and flags resolution events when recovery logs are detected.

### 3.5 Cluster Health Engine
Formulates real-time health scores (0-100) per node by applying weight-based deductions for active incidents and warnings. Classifies overall cluster status as Healthy, Warning, or Critical.

### 3.6 AI RCA Engine
Orchestrates prompt creation, caching (`storage/ai_analysis.json`), and error retries for LLM executions. It exposes a single interface (`generate_rca`) backed by a Factory Pattern supporting Google Gemini and Azure OpenAI.

---

## 4. Data Flow
1. **Generation**: The simulator writes logs to disk.
2. **Ingestion & Parsing**: On refresh, the parser seeks to the saved byte offset, reads lines, converts them to JSON, and updates offset.
3. **Detection**: The processor executes SRE rules against new logs, appending matching anomalies to database.
4. **Correlation**: Anomalies are grouped into active incidents. Timeline arrays are compiled.
5. **Score Allocation**: The health engine reads active incidents and evaluates health scores.
6. **AI Analysis**: Upon manual or automatic triggers, the RCA engine constructs SRE context prompts, checks the cache, queries Gemini/Azure, validates JSON structures, and returns results.

---

## 5. Technology Choices
- **Streamlit**: Selected for rapid front-end prototyping, reactive interface rendering, and seamless python background thread execution.
- **JSON File-Based Store**: Implemented to meet "no database" constraints while ensuring persistent state that survives page reloads.
- **Official SDKs**: Utilized `openai` and `google-generativeai` to guarantee native API feature support.
- **Plotly Express**: Used for dynamic time-series scatter plots to map anomalies chronologically.

---

## 6. Design Decisions
- **Manual AI Triggering**: Selected by default to minimize API call quotas and token usage on free developer tiers.
- **Zero Raw Log Transfer to LLMs**: Restricting context to correlated incidents guarantees security (no IP/confidential log data leaks) and reduces token complexity.
- **Strict Temperature=0**: Set to eliminate LLM creativity and guarantee deterministic root cause summaries.

---

## 7. Scalability Considerations
- **Disk Buffering**: Relying on local log files buffers spikes in network throughput.
- **Database Partitioning**: For larger production clusters, the JSON files should be replaced by structured time-series databases (e.g., TimescaleDB, InfluxDB) and document indexes (Elasticsearch).
- **Log Collectors**: Ingest pipeline should use stateless forwarders (FluentBit, Logstash) writing to message brokers (Kafka) rather than local file polling.

---

## 8. Security Considerations
- **Environment Isolation**: API credentials are loaded strictly from `.env` files and never committed to source control.
- **Anonymized Metadata**: By sending only incident timelines (anonymized system parameters, GC transitions, component names), no sensitive enterprise logs leave the trust boundary.

---

## 9. Production Deployment Considerations
- **Containerization**: Deployable via Docker Compose containing isolated containers for Streamlit, the log collector pipeline, and local storage mounts.
- **Kubernetes**: Stateful sets for Solr, DaemonSets for FluentBit, and deployments for the parser/observability dashboard.

---

## 10. Observability Considerations
- **Internal Tracing**: The application uses Python's standard `logging` module to output debug and warning statements during pipeline runs.
- **Audit Logging**: AI requests, costs, and token usages are logged for cost control.

---

## 11. Future Enhancements
- **Multi-tenant isolation** to support several independent SolrCloud clusters.
- **Semantic search index** on historical incidents to accelerate retrieval of past SRE resolutions.
