#!/usr/bin/env python3
"""
app.py

AI Powered Solr Observability Platform Dashboard.
Integrates event processing pipeline, health metrics, anomaly lists, active incidents,
and AI-powered Root Cause Analysis using Azure OpenAI / Google Gemini.
"""

import time
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# Setup paths and imports
BASE_DIR = Path(__file__).resolve().parent

import sys
sys.path.append(str(BASE_DIR))

from generator.generate_logs import get_generator, NODE_NAMES
from processor.event_processor import EventProcessor
from llm.rca_engine import RCAEngine
from config.settings import Settings

# Page Configuration
st.set_page_config(
    page_title="AI Solr Observability",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #1a1a1a;
    }
    .metric-label {
        font-size: 13px;
        color: #666666;
        text-transform: uppercase;
        margin-top: 5px;
    }
    .incident-timeline-item {
        padding: 8px;
        border-left: 2px solid #0066cc;
        margin-left: 10px;
        margin-bottom: 5px;
        background-color: #fcfcfc;
    }
    .ai-panel {
        background-color: #f0f7ff;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #b3d7ff;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize singletons
generator = get_generator(BASE_DIR)
processor = EventProcessor(BASE_DIR)
rca_engine = RCAEngine(BASE_DIR)

# Execute the central Event Processor Pipeline on refresh
health_info = processor.process()

# Load logs, anomalies, and incidents
df_logs = pd.DataFrame(processor.parser.load_parsed_logs())
df_anomalies = pd.DataFrame(processor.load_anomalies())
incidents = processor.load_incidents()
df_incidents = pd.DataFrame([i.to_dict() for i in incidents]) if incidents else pd.DataFrame()

# Sidebar controls
st.sidebar.title("🛠️ Platform Settings")

# Simulation controls
with generator.lock():
    sim_status = generator.status

if sim_status == "RUNNING":
    st.sidebar.success("Simulation: RUNNING")
    if st.sidebar.button("⏸️ Pause Simulation"):
        generator.pause()
        st.rerun()
else:
    st.sidebar.warning(f"Simulation: {sim_status}")
    if st.sidebar.button("▶️ Start Simulation"):
        generator.start()
        st.rerun()

# Scenario Injection dropdown
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Inject Failure Scenario")
injectable_scenarios = [
    "Memory Leak",
    "ZooKeeper Failure",
    "Disk Failure",
    "Network Failure",
    "CPU Spike",
    "Heap Pressure",
    "Heavy Indexing"
]
selected_scenario = st.sidebar.selectbox("Select Scenario", injectable_scenarios)
if st.sidebar.button("⚡ Inject Incident"):
    generator.inject_scenario(selected_scenario)
    st.sidebar.info(f"Injected {selected_scenario} into simulated cluster!")
    time.sleep(0.5)

# AI Settings Overrides in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI settings")

# Session state overrides
default_provider = Settings.get_provider()
provider_options = ["gemini", "azure"]
initial_provider_idx = provider_options.index(default_provider) if default_provider in provider_options else 0

selected_provider = st.sidebar.selectbox("AI Provider", provider_options, index=initial_provider_idx)

# Determine default models
default_model = ""
if selected_provider == "azure":
    default_model = Settings.get_azure_config().get("deployment", "gpt-4")
else:
    default_model = Settings.get_gemini_config().get("model", "gemini-2.5-flash")

model_name = st.sidebar.text_input("Model / Deployment", value=default_model)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
max_tokens = st.sidebar.slider("Max Tokens", min_value=100, max_value=2000, value=1200, step=100)

ai_mode = st.sidebar.radio("AI Analysis Mode", ["Manual (Recommended)", "Automatic"], index=0)

if st.sidebar.button("🧹 Clear AI Cache"):
    rca_engine.clear_cache()
    st.sidebar.success("AI Cache cleared successfully!")
    time.sleep(0.5)
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Platform"):
    generator.pause()
    generator.reset_files()
    processor.parser.clear_state()
    processor.clear_state()
    rca_engine.clear_cache()
    st.success("Platform database and log streams reset!")
    time.sleep(1)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Refresh Rate")
auto_refresh = st.sidebar.toggle("Auto Refresh Dashboard", value=True)
refresh_interval_str = st.sidebar.selectbox("Interval", ["1 sec", "2 sec", "5 sec"], index=1)
refresh_interval = int(refresh_interval_str.split()[0])

# Main Observability Header
st.title("🔍 AI Powered Solr Observability Platform")
st.subheader("Live Cluster Monitoring & Root Cause Analysis Pipeline")

# Process metric values
healthy_nodes_count = health_info.get("healthy_nodes", 5)
warning_nodes_count = health_info.get("warning_nodes", 0)
critical_nodes_count = health_info.get("critical_nodes", 0)
active_incidents_count = health_info.get("active_incidents", 0)
total_parsed_logs = len(df_logs)
open_alerts_count = len(df_anomalies[df_anomalies["severity"] == "Critical"]) if not df_anomalies.empty else 0

# Render Top KPI row
kpi_cols = st.columns(7)
kpi_data = [
    ("Healthy Nodes", f"{healthy_nodes_count} / 5", "#28a745"),
    ("Warning Nodes", str(warning_nodes_count), "#ffc107"),
    ("Critical Nodes", str(critical_nodes_count), "#dc3545"),
    ("Active Incidents", str(active_incidents_count), "#fd7e14"),
    ("Open Critical Alerts", str(open_alerts_count), "#d63384"),
    ("Total Parsed Logs", str(total_parsed_logs), "#0066cc"),
    ("Simulation Status", sim_status, "#6f42c1" if sim_status == "RUNNING" else "#6c757d")
]

for col, (label, val, border_color) in zip(kpi_cols, kpi_data):
    with col:
        st.markdown(f"""
            <div class="metric-card" style="border-top: 4px solid {border_color};">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# Node health summary overview
st.subheader("🖥️ Cluster Health Overview")
node_details = health_info.get("nodes", {})
node_rows = []
for node in NODE_NAMES:
    n_info = node_details.get(node, {"score": 100, "status": "Healthy"})
    score = n_info["score"]
    status = n_info["status"]
    
    # Get last incident details
    last_node_inc = [i for i in incidents if i.node == node]
    last_inc_id = last_node_inc[-1].id if last_node_inc else "None"
    
    # Get recent warnings count
    recent_warns = 0
    if not df_anomalies.empty:
        recent_warns = len(df_anomalies[(df_anomalies["node"] == node) & (df_anomalies["severity"] == "Warning")])
        
    node_rows.append({
        "Node": node,
        "Health Score": f"{score}/100",
        "Status": status,
        "Last Incident": last_inc_id,
        "Recent Warnings": recent_warns
    })

df_node_summary = pd.DataFrame(node_rows)
st.dataframe(df_node_summary, use_container_width=True, hide_index=True)

st.markdown("---")

# Incident Timeline visualization
st.subheader("📊 Incident Timeline Graph")
if not df_anomalies.empty:
    fig = px.scatter(
        df_anomalies,
        x="timestamp",
        y="node",
        color="severity",
        size=[10] * len(df_anomalies),
        hover_data=["rule", "category", "message"],
        color_discrete_map={"Critical": "#dc3545", "Warning": "#ffc107", "Info": "#28a745"},
        title="Detected Anomalies Over Time"
    )
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Node",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        height=280
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No anomalies detected yet to populate timeline chart.")

st.markdown("---")

# Expandable Active Incidents Section
st.subheader("🚨 Active Incidents")
active_incs = [i for i in incidents if i.status == "Active"]
if active_incs:
    for inc in active_incs:
        # Generate clean state variable for button click tracking
        button_key = f"run_ai_{inc.id}"
        if button_key not in st.session_state:
            st.session_state[button_key] = False

        color = "red" if inc.severity == "Critical" else "orange"
        with st.expander(f"⚠️ {inc.id} - Severity: {inc.severity} | Node: {inc.node} | Category: {inc.category} (Active)"):
            st.write(f"**Started:** {inc.start_time} | **Duration:** {int(inc.duration)} seconds")
            st.write(f"**Timeline Events ({inc.num_anomalies}):**")
            for t_event in inc.timeline:
                st.markdown(f"""
                    <div class="incident-timeline-item">
                        <small style='color: gray;'>{t_event['timestamp']}</small><br/>
                        {t_event['message']}
                    </div>
                """, unsafe_allow_html=True)
                
            # Explain with AI Button logic
            run_ai = False
            if ai_mode == "Automatic" and inc.severity == "Critical":
                run_ai = True
            else:
                if st.button(f"🤖 Explain {inc.id} with AI", key=f"btn_{inc.id}"):
                    st.session_state[button_key] = True
                run_ai = st.session_state[button_key]
                
            if run_ai:
                with st.spinner("AI SRE is analyzing incident context..."):
                    # Call LLM RCA Engine
                    analysis = rca_engine.analyze_incident(
                        inc.to_dict(),
                        cluster_health=health_info.get("overall_status", "Healthy"),
                        provider_override=selected_provider,
                        model_override=model_name,
                        temp_override=temperature,
                        tokens_override=max_tokens
                    )
                    
                # Display SRE Analysis Panel
                st.markdown(f"""
                    <div class="ai-panel">
                        <h4>🤖 AI Root Cause Analysis</h4>
                        <p><strong>Executive Summary:</strong> {analysis.get('summary', '')}</p>
                        <p><strong>Detected Root Cause:</strong> {analysis.get('root_cause', '')}</p>
                        <p><strong>Business Impact:</strong> {analysis.get('business_impact', '')}</p>
                        <p><strong>Operational Recommendations:</strong></p>
                        <ul>
                            {"".join([f"<li>{r}</li>" for r in analysis.get('recommendations', [])])}
                        </ul>
                        <p><strong>Priority Level:</strong> {analysis.get('priority', 'Medium')} | <strong>Confidence Score:</strong> {analysis.get('confidence', 0.0)*100:.1f}%</p>
                    </div>
                """, unsafe_allow_html=True)
else:
    st.success("No active incidents. The cluster is running clean!")

st.markdown("---")

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 Active Incidents", 
    "📈 Detected Anomalies", 
    "📝 Live Solr Logs", 
    "⚙️ Live GC Logs", 
    "📊 Parsed Events"
])

with tab1:
    st.write("Complete incident list (active and resolved).")
    if not df_incidents.empty:
        display_incidents = df_incidents[["id", "node", "category", "severity", "status", "start_time", "duration", "num_anomalies"]].iloc[::-1]
        st.dataframe(display_incidents, use_container_width=True, hide_index=True)
    else:
        st.info("No incidents created yet.")

with tab2:
    st.write("All rule-matched anomalies parsed in real-time.")
    if not df_anomalies.empty:
        display_anoms = df_anomalies[["timestamp", "node", "severity", "rule", "category", "source", "message"]].iloc[::-1]
        st.dataframe(display_anoms, use_container_width=True, hide_index=True)
    else:
        st.info("No anomalies detected yet.")

with tab3:
    if not df_logs.empty:
        solr_df = df_logs[df_logs["source"] == "solr"].copy()
        if not solr_df.empty:
            solr_display = solr_df[["timestamp", "node", "level", "component", "message"]].iloc[::-1]
            st.dataframe(solr_display, use_container_width=True, hide_index=True, height=350)
        else:
            st.info("No Solr log entries found yet.")
    else:
        st.info("No logs present. Start simulation.")

with tab4:
    if not df_logs.empty:
        gc_df = df_logs[df_logs["source"] == "gc"].copy()
        if not gc_df.empty:
            gc_display = gc_df[["timestamp", "node", "message"]].iloc[::-1]
            st.dataframe(gc_display, use_container_width=True, hide_index=True, height=350)
        else:
            st.info("No GC log entries found yet.")
    else:
        st.info("No logs present. Start simulation.")

with tab5:
    if not df_logs.empty:
        all_display = df_logs[["timestamp", "node", "source", "level", "component", "message"]].iloc[::-1]
        st.dataframe(all_display, use_container_width=True, hide_index=True, height=350)
    else:
        st.info("No parsed event logs.")

# Dashboard Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
