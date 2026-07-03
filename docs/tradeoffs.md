# Architectural Tradeoffs

## Table of Contents
1. [Overview](#1-overview)
2. [Design Decision Matrix](#2-design-decision-matrix)
3. [Key Architectural Tradeoffs](#3-key-architectural-tradeoffs)
4. [Transitioning to Production](#4-transitioning-to-production)

---

## 1. Overview
This document evaluates the architectural tradeoffs accepted during Phase 2 & 3. It contrasts the lightweight development stack against a full production deployment setup.

---

## 2. Design Decision Matrix

| Metric / Parameter | Lightweight Choice | Production Choice | Rationale |
| :--- | :--- | :--- | :--- |
| **Storage Engine** | Local JSON Files | TimescaleDB / Elasticsearch | Minimizes dependency overhead; easily queryable for dashboard prototype. |
| **Telemetry Ingestion**| Incremental File Parser | Kafka / Logstash / FluentBit | Fast implementation; no active streaming infrastructure required. |
| **Dashboard UI** | Streamlit | React / Grafana | Enables rapid Python prototyping and easy state persistence. |
| **Cache Store** | Local JSON Cache | Redis | Simplifies development; no persistent daemon installation needed. |
| **RCA Processing** | Manual + Auto Trigger | Background Queue (Celery) | Limits LLM costs on developer keys; keeps interactive demonstration snappy. |

---

## 3. Key Architectural Tradeoffs

### 3.1 JSON Storage vs. Structured Database
- **Tradeoff**: Reading/writing JSON databases requires complete file loads and rewrites.
- **Why**: Avoids setting up database servers (PostgreSQL/MySQL), simplifying deployment and keeping the codebase self-contained.

### 3.2 Streamlit vs. Production Front-end (React/Grafana)
- **Tradeoff**: Streamlit reruns the entire script on page interaction, limiting complex UI controls.
- **Why**: Reuses python models and SRE logic directly without building web APIs, authentication, and CORS handling.

### 3.3 Rule-Based Engine vs. Machine Learning Models
- **Tradeoff**: Rules require SRE curation and regular maintenance.
- **Why**: Delivers instant cold-start anomaly classification, requires zero inference hardware, and operates with absolute transparency.

### 3.4 Decoupled Event Pipeline vs. Kafka/Elasticsearch Ingestion
- **Tradeoff**: Incremental parser requires direct filesystem access and does not scale horizontally.
- **Why**: Simple setup that runs directly in standard dev workspaces without installing Docker clusters.

---

## 4. Transitioning to Production
To scale this architecture to a live enterprise SolrCloud deployment, the following changes are recommended:
1. **Replace JSON Store** with a hybrid backend: Elasticsearch for raw log indexing and PostgreSQL/TimescaleDB for incident/alert analytics.
2. **Move Ingest to FluentBit**: Replace the custom python parser with standard DaemonSets forwarding to Kafka topics.
3. **Containerize Services**: Separate the background processor and web interface into Kubernetes pods.
4. **Implement Redis Caching**: Replace the JSON cache with a shared Redis instance to handle concurrent requests.
