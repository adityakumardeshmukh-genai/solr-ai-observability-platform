# AI Powered Solr Observability & Root Cause Analysis Platform

## Table of Contents
1. [Overview](#1-overview)
2. [Objectives](#2-objectives)
3. [Key Features](#3-key-features)
4. [Technology Stack](#4-technology-stack)
5. [Architecture Overview](#5-architecture-overview)
6. [Project Folder Structure](#6-project-folder-structure)
7. [Installation](#7-installation)
8. [Environment Variables](#8-environment-variables)
9. [How to Run](#9-how-to-run)
10. [Application Workflow](#10-application-workflow)
11. [Screenshots](#11-screenshots)
12. [Project Highlights](#12-project-highlights)
13. [Future Scope](#13-future-scope)
14. [License](#14-license)

---

## 1. Overview
The **AI Powered Solr Observability & Root Cause Analysis Platform** is an SRE tool designed to monitor distributed Apache SolrCloud clusters. It simulates a 5-node cluster state, parses logs incrementally, matches SRE rule thresholds, correlates anomalies into grouped incidents, and calls Google Gemini or Azure OpenAI to generate root cause analysis, business impact, and remediation recommendations.

---

## 2. Objectives
- **Decoupled Diagnostics**: Correlate system anomalies locally to ensure only high-level incidents are sent to the LLM (no raw logs).
- **Extensible Factory Structure**: Easily switch between LLM providers using environment variables.
- **Rule-Based Engine Accuracy**: Enable instant anomaly classifications without cold-start training delays.

---

## 3. Key Features
- **Live SolrCloud Log Simulation**: Appends query executions, merges, ZooKeeper events, and commit cycles.
- **Live JVM GC Simulation**: Generates multi-line G1GC logs for Young, Mixed, and Full GC cycles.
- **Incremental Log Parsing**: Ingests new log lines using file byte offset tracking.
- **Rule-Based Anomaly Detection**: Evaluates events against deterministic rules.
- **Event Correlation**: Clusters matching host/category anomalies into incidents within a 5-minute sliding window.
- **Cluster Health Monitoring**: Computes real-time node health scores (0-100).
- **AI Powered Root Cause Analysis**: Resolves issues using Large Language Models.
- **Multi-Provider LLM Factory**: Hot-swap between Google Gemini and Azure OpenAI.
- **Interactive Streamlit Dashboard**: Displays status grids, Plotly charts, and logs.
- **Live Incident Simulation**: Instantly inject failures like Memory Leaks or ZooKeeper disconnects.

---

## 4. Technology Stack
- **Language**: Python 3.12+
- **Front-end / Dashboard**: Streamlit
- **Data Analytics**: Pandas
- **Visualization**: Plotly Express
- **LLM Integrations**: Google GenAI SDK (`google-generativeai`), Azure OpenAI SDK (`openai`), `python-dotenv`
- **Storage**: Local JSON files (`parsed_logs.json`, `anomalies.json`, `incidents.json`, `cluster_health.json`, `ai_analysis.json`)

---

## 5. Architecture Overview
Refer to [architecture.md](docs/architecture.md) for full details.

---

## 6. Project Folder Structure
```text
solr-observability/
├── app.py                     # Streamlit application
├── requirements.txt           # Python packages list
├── .env                       # Environment configuration keys
├── generator/
│   └── generate_logs.py       # Live simulator engine
├── parser/
│   └── parser.py              # Incremental byte offset parser
├── detector/
│   └── anomaly_detector.py    # Rule matching engine
├── correlation/
│   └── correlation_engine.py  # Groups anomalies into incidents
├── health/
│   └── cluster_health.py      # Health score generator
├── processor/
│   └── event_processor.py     # Central pipeline coordinator
├── llm/
│   ├── provider.py            # Abstract provider factory interface
│   ├── openai_provider.py     # Azure OpenAI client implementation
│   ├── gemini_provider.py     # Google Gemini client implementation
│   ├── prompt_builder.py      # SRE SRE Prompt compiler
│   ├── response_parser.py     # Response format cleaner
│   └── rca_engine.py          # Cache and retry manager
├── prompts/
│   └── rca_prompt.txt         # SRE system template
├── storage/
│   ├── parsed_logs.json
│   ├── parser_state.json
│   ├── anomalies.json
│   ├── incidents.json
│   ├── cluster_health.json
│   └── ai_analysis.json       # Cache store
└── logs/
    ├── solr.log
    └── gc.log
```

---

## 7. Installation
```bash
# Clone the repository and navigate to the directory
cd solr-observability

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 8. Environment Variables
Create a `.env` file in the root folder:
```ini
LLM_PROVIDER=gemini # gemini or azure

# --- Google Gemini Settings ---
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.0-flash

# --- Azure OpenAI Settings ---
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=YOUR_AZURE_KEY
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# --- Optional Inference Params ---
TEMPERATURE=0
MAX_TOKENS=1200
```

---

## 9. How to Run
```bash
# Execute the Streamlit application
streamlit run app.py
```

---

## 10. Application Workflow
1. **Startup**: Instantiates log files and starts the background generator thread.
2. **Simulation**: Appends background query logs. Users can inject failures (e.g. *Memory Leak*) from the sidebar.
3. **Parse & Detect**: The event processor pipeline reads new telemetry, matches rules, and writes anomalies.
4. **Correlate**: Anomalies are grouped into incidents. Node health scores are updated.
5. **AI Diagnose**: SREs click `Explain with AI` on an incident to fetch root cause diagnostics.

---

## 11. Screenshots

### Dashboard
<img width="1043" height="327" alt="image" src="https://github.com/user-attachments/assets/1c4b3e17-fc99-494a-b43d-6ed8e225f5b9" />


### Incident Cards
<img width="1353" height="191" alt="image" src="https://github.com/user-attachments/assets/ee062221-17a1-4eb6-ae94-39375bc4a763" />


### Cluster Health
<img width="1296" height="366" alt="image" src="https://github.com/user-attachments/assets/fe21d34b-db7d-4e75-970f-d420980bb29d" />


### AI RCA
<img width="1302" height="745" alt="image" src="https://github.com/user-attachments/assets/af73815f-2422-4ff5-a87b-300a38e74230" />


### Active Incidents
<img width="1325" height="452" alt="image" src="https://github.com/user-attachments/assets/5f17e2f6-ada4-447d-8676-82d024686d41" />

### Live Logs
<img width="1338" height="442" alt="image" src="https://github.com/user-attachments/assets/ea2bed20-ae62-4f43-9622-fb803c2459e2" />

### Simulation Controls
<img width="327" height="816" alt="image" src="https://github.com/user-attachments/assets/71e49d23-2dbe-43df-b079-4d5de1c26157" />


### Demo GIF (Optional)
[ Add Screenshot Here ]

---

## 12. Project Highlights
- **No Raw Logs Transferred**: Safeguards enterprise IP by sharing only structured incident timelines.
- **Determinism Guaranteed**: Temperature=0 eliminates hallucinations.
- **Caching Layer**: Saves money and decreases response times using local caching.

---

## 13. Future Scope
- Transition to Kafka ingestion.
- Store incidents in Elasticsearch.
- Build dynamic threshold models to baseline normal behavior.

---

## 14. License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
