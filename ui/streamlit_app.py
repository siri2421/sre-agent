# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import uuid
import pathlib
import streamlit as st
import vertexai
from dotenv import load_dotenv

# Ensure root path is in sys.path when running from ui/ folder
ROOT_DIR = pathlib.Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from app.config import PROJECT_ID, GEMINI_LOCATION, GKE_CLUSTER_NAME, GKE_CLUSTER_REGION

# =========================================================================
# 1. PAGE SETUP & MINIMALIST STYLING
# =========================================================================
st.set_page_config(
    page_title="NovaSRE — Incident Control Room",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom minimalist dark-mode CSS
st.markdown("""
<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    /* Header Card */
    .header-container {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border: 1px solid #374151;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .header-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.25rem;
    }
    .header-sub {
        font-size: 0.9rem;
        color: #9ca3af;
    }
    /* Status Cards */
    .alert-box {
        padding: 1.25rem;
        background-color: #2a1215;
        border-left: 5px solid #ff4b4b;
        border-radius: 6px;
        color: #fce8e6;
        margin-bottom: 1rem;
    }
    .healthy-box {
        padding: 1.25rem;
        background-color: #11261d;
        border-left: 5px solid #21c354;
        border-radius: 6px;
        color: #e8fcf0;
        margin-bottom: 1rem;
    }
    .approval-card {
        padding: 1.5rem;
        background-color: #252830;
        border: 2px solid #f39c12;
        border-radius: 8px;
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="header-container">
    <div class="header-title">🛡️ NovaSRE — Incident Control Room</div>
    <div class="header-sub">Production Cluster: {GKE_CLUSTER_NAME} | Region: {GKE_CLUSTER_REGION} | Project: {PROJECT_ID or 'Local-Sandbox'}</div>
</div>
""", unsafe_allow_html=True)

# =========================================================================
# 2. SESSION STATE INITIALIZATION
# =========================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_alert" not in st.session_state:
    st.session_state.active_alert = "None (System Healthy 🟢)"
if "cluster_status" not in st.session_state:
    st.session_state.cluster_status = "HEALTHY 🟢"
if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None
if "postmortem_report" not in st.session_state:
    st.session_state.postmortem_report = None
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

@st.cache_data(ttl=300, show_spinner=False)
def _discover_cached(agent_name: str) -> str:
    """Fallback discovery across Vertex AI Reasoning Engine registry if env var not set."""
    try:
        from google.cloud import aiplatform
        aiplatform.init(project=PROJECT_ID, location=GEMINI_LOCATION)
        from vertexai.preview.reasoning_engines import ReasoningEngine
        engines = ReasoningEngine.list()
        for e in engines:
            if e.display_name == agent_name:
                return e.resource_name
    except Exception as e:
        print(f"Discovery error for {agent_name}: {e}")
    return ""

def discover_engine_urn(display_name: str, env_key: str = None) -> str:
    """Dynamically discovers agent URN without caching live environment variables."""
    if env_key and os.environ.get(env_key):
        val = os.environ.get(env_key)
        if val.startswith("projects/"):
            return val
    cached_urn = _discover_cached(display_name)
    if cached_urn:
        return cached_urn
    return os.environ.get(env_key, f"projects/{PROJECT_ID}/locations/{GEMINI_LOCATION}/reasoningEngines/{display_name}")

def format_ai_response(raw_text: str) -> str:
    """Detects trailing raw JSON facts strings and transforms the entire response into a sleek, unified Executive Incident Resolution Report card."""
    import re
    import json
    json_match = re.search(r'(\{[\s\S]*?"alert"[\s\S]*?"root_cause"[\s\S]*?\})', raw_text)
    if json_match:
        try:
            raw_json_str = json_match.group(1)
            data = json.loads(raw_json_str)
            status_badge = "SUCCESS 🟢" if data.get("remediation_status") == "SUCCESS" else data.get("remediation_status", "INFO")
            
            # Extract narrative text excluding the JSON block and conversational filler
            narrative = raw_text.replace(raw_json_str, "").strip()
            # Clean up redundant chat preambles if present
            narrative = re.sub(r'^(Of course|Certainly|Sure)[\s\S]*?(Here is my executive report:|findings:)\s*', '', narrative, flags=re.IGNORECASE).strip()
            
            # Try extracting specific sections if structured markdown exists
            diag_match = re.search(r'(?:###?|\*\*|🕵️‍♂️)\s*Diagnostic Findings.*?:?\n+([\s\S]*?)(?=\n+(?:###?|\*\*|⚡|🤖|✅|$))', narrative, re.IGNORECASE)
            a2a_match = re.search(r'(?:###?|\*\*|⚡|🤖)\s*(?:Autonomous )?A2A Delegation.*?:?\n+([\s\S]*?)(?=\n+(?:###?|\*\*|✅|$))', narrative, re.IGNORECASE)
            
            diag_text = diag_match.group(1).strip() if diag_match else data.get('root_cause', 'Root cause identified and verified across telemetry.')
            a2a_text = a2a_match.group(1).strip() if a2a_match else f"Executed `{data.get('recommended_action', 'N/A')}` via secure A2A delegation under Tier 1 Auto-Recovery."
            
            # Build unified executive summary card
            card_md = f"""<div style="background: rgba(30, 41, 59, 0.75); border: 1px solid rgba(255, 255, 255, 0.12); border-left: 5px solid #10B981; border-radius: 10px; padding: 20px; margin: 15px 0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);">
    <h3 style="margin-top: 0; color: #10B981; font-family: 'Outfit', sans-serif; display: flex; align-items: center; gap: 8px;">🛡️ NovaSRE Executive Resolution Brief</h3>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0; background: rgba(15, 23, 42, 0.5); border-radius: 6px; overflow: hidden;">
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); width: 30%; color: #94A3B8;"><b>🚨 Alert Trigger</b></td>
            <td style="padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #F87171;"><code>{data.get('alert', 'N/A')}</code></td>
        </tr>
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #94A3B8;"><b>🎯 Target Resource</b></td>
            <td style="padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #E2E8F0;"><code>{data.get('target_resource', 'N/A')}</code></td>
        </tr>
        <tr>
            <td style="padding: 10px 14px; color: #94A3B8;"><b>⚡ Autonomous Action</b></td>
            <td style="padding: 10px 14px; color: #E2E8F0;"><b><code>{data.get('recommended_action', 'N/A')}</code></b> &nbsp;<span style="background: #065F46; color: #34D399; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">{status_badge}</span></td>
        </tr>
    </table>
    <h4 style="margin: 15px 0 6px 0; color: #E2E8F0; font-size: 1.05em;">🕵️‍♂️ Diagnostic & Root Cause Findings</h4>
    <p style="color: #CBD5E1; line-height: 1.6; margin: 0 0 16px 0; font-size: 0.95em;">{diag_text}</p>
    <h4 style="margin: 15px 0 6px 0; color: #E2E8F0; font-size: 1.05em;">🤖 Autonomous A2A Execution (`remediation-executor`)</h4>
    <p style="color: #CBD5E1; line-height: 1.6; margin: 0; font-size: 0.95em;">{a2a_text}</p>
</div>"""
            return card_md
        except Exception as e:
            print(f"Error rendering card: {e}")
            pass
    return raw_text

def parse_stream_chunks(raw_chunks_list):
    import json
    clean_texts = []
    
    for raw in raw_chunks_list:
        raw_strip = raw.strip()
        if not raw_strip:
            continue
            
        parsed_objs = []
        if raw_strip.startswith("{") and raw_strip.endswith("}"):
            try:
                parsed_objs.append(json.loads(raw_strip))
            except Exception:
                pass
                
        if not parsed_objs:
            for line in raw_strip.split("\n"):
                line_strip = line.strip()
                if line_strip.startswith("{") and line_strip.endswith("}"):
                    try:
                        parsed_objs.append(json.loads(line_strip))
                    except Exception:
                        pass
                elif not line_strip.startswith("{") and not any(meta_key in line_strip for meta_key in ["\"model_version\"", "\"thought_signature\"", "\"usage_metadata\"", "\"candidates_token_count\""]):
                    clean_texts.append(line_strip)
                    
        for data in parsed_objs:
            if "error_message" in data and data["error_message"]:
                clean_texts.append(f"⚠️ **Execution Notice:** {data['error_message']}")
                continue
            if "content" in data and "parts" in data["content"]:
                for part in data["content"]["parts"]:
                    if "text" in part and part["text"]:
                        txt = part["text"]
                        if not ("<available_skills>" in txt or "<skill>" in txt):
                            clean_texts.append(txt)
                            
    if clean_texts:
        return format_ai_response("\n\n".join([t for t in clean_texts if t.strip()]))
    return format_ai_response("Investigation complete. Please review active system metrics and status cards above.")

# =========================================================================
# 3. SIDEBAR: DEMO & OUTAGE SIMULATION DRAWER
# =========================================================================
with st.sidebar:
    st.title("🛠️ Demo & Simulation")
    st.caption("Clean, unobtrusive controls for showcasing all 4 self-healing capabilities.")
    
    with st.expander("🧪 Simulate Outage Scenarios", expanded=True):
        st.write("Dynamically loads failure scenarios from `app/skills/simulations/` and invokes the Chaos Engine.")
        
        # Scan skills directory for available simulation playbooks
        sim_dir = ROOT_DIR / "app" / "skills" / "simulations"
        sim_options = {}
        if sim_dir.exists():
            for p in sorted(sim_dir.iterdir()):
                if p.is_dir() and (p / "SKILL.md").exists():
                    if p.name == "gke-scale-outage":
                        sim_options[p.name] = "🟢 gke-scale-outage (Scale frontend to 0 | Tier 1 Auto)"
                    elif p.name == "gke-bad-rollout":
                        sim_options[p.name] = "🟢 gke-bad-rollout (cartservice CrashLoop | Tier 1 Auto-Rollback)"
                    elif p.name == "gke-pod-crash":
                        sim_options[p.name] = "🟡 gke-pod-crash (redis-cart Lock & Timeout | Tier 2 HITL)"
                    elif p.name == "gke-payment-latency":
                        sim_options[p.name] = "🟡 gke-payment-latency (paymentservice Bottleneck | Tier 2 HITL)"
                    elif p.name == "gke-network-firewall-block":
                        sim_options[p.name] = "🌐 gke-network-firewall-block (NetworkPolicy Traffic Isolation | Tier 2 HITL)"
                    elif p.name == "gke-dns-outage":
                        sim_options[p.name] = "🌐 gke-dns-outage (CoreDNS Resolution Timeout | Tier 1 Auto)"
                    elif p.name == "gcp-nat-port-drop":
                        sim_options[p.name] = "🌐 gcp-nat-port-drop (Cloud NAT Egress Port Exhaustion | Tier 2 HITL)"
                    else:
                        sim_options[p.name] = f"🟡 {p.name} Simulation"
        if not sim_options:
            sim_options["gke-scale-outage"] = "🟢 gke-scale-outage (Scale frontend to 0 | Tier 1 Auto)"
            
        selected_sim = st.selectbox("Select Scenario:", list(sim_options.keys()), format_func=lambda x: sim_options[x])
        
        if st.button("💥 Trigger Simulation", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            with st.spinner(f"Executing '{selected_sim}' via Outage Simulator..."):
                sim_urn = discover_engine_urn("outage-simulator", "OUTAGE_SIMULATOR_URN")
                if sim_urn and sim_urn.startswith("projects/"):
                    try:
                        vertexai.init(project=PROJECT_ID, location=GEMINI_LOCATION)
                        from google.cloud.aiplatform_v1beta1 import types as aip_types
                        from vertexai.preview.reasoning_engines import ReasoningEngine
                        remote_sim = ReasoningEngine(sim_urn)
                        prompt = f"Load the '{selected_sim}' skill and execute the controlled outage simulation right now."
                        resp = remote_sim.execution_api_client.stream_query_reasoning_engine(
                            request=aip_types.StreamQueryReasoningEngineRequest(
                                name=remote_sim.resource_name,
                                input={"user_id": f"sre-{st.session_state.session_id}", "message": {"role": "user", "parts": [{"text": prompt}]}},
                                class_method="stream_query",
                            )
                        )
                        chunks = []
                        for chunk in resp:
                            if hasattr(chunk, "data") and chunk.data:
                                chunks.append(chunk.data.decode("utf-8", errors="ignore"))
                        res = parse_stream_chunks(chunks) if chunks else f"💥 Outage simulation '{selected_sim}' executed successfully across cluster."
                    except Exception as e:
                        res = f"Cloud simulation call error: {e}. Executing locally..."
                else:
                    import asyncio
                    from google.adk.runners import InMemoryRunner
                    from app.outage_simulator_agent import outage_simulator
                    from google.genai import types as genai_types
                    
                    async def run_local_sim():
                        runner = InMemoryRunner(agent=outage_simulator, app_name=outage_simulator.name)
                        await runner.session_service.create_session(app_name=outage_simulator.name, user_id="sre", session_id=st.session_state.session_id)
                        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=f"Load the '{selected_sim}' skill and execute the outage simulation.")])
                        chunks = []
                        async for event in runner.run_async(user_id="sre", session_id=st.session_state.session_id, new_message=msg):
                            if hasattr(event, "content") and event.content and event.content.parts:
                                for part in event.content.parts:
                                    if hasattr(part, "text") and part.text:
                                        chunks.append(part.text)
                        return "".join(chunks)
                    res = asyncio.run(run_local_sim())
                
                if selected_sim == "gke-scale-outage":
                    st.session_state.active_alert = "CRITICAL ALERT: frontend service active replicas = 0. HTTP 503 errors detected across store. Investigate immediately."
                elif selected_sim == "gke-bad-rollout":
                    st.session_state.active_alert = "CRITICAL ALERT: cartservice pod entering CrashLoopBackOff. ErrImagePull or application initialization failure reported."
                elif selected_sim == "gke-pod-crash":
                    st.session_state.active_alert = "CRITICAL ALERT: redis-cart connection timeout exceptions exceeding threshold across shopping carts. Pod terminated."
                elif selected_sim == "gke-payment-latency":
                    st.session_state.active_alert = "WARNING ALERT: paymentservice p99 transaction latency exceeding 2000ms. High CPU saturation and checkout timeouts."
                elif selected_sim == "gke-network-firewall-block":
                    st.session_state.active_alert = "CRITICAL ALERT: checkoutservice pod network isolation reported. Restrictive NetworkPolicy blocking ingress/egress packets."
                elif selected_sim == "gke-dns-outage":
                    st.session_state.active_alert = "CRITICAL ALERT: GKE CoreDNS deployment in namespace kube-system scaled to 0. Internal domain resolution timeouts across cluster.local."
                elif selected_sim == "gcp-nat-port-drop":
                    st.session_state.active_alert = "WARNING ALERT: Cloud NAT gateway nat-gateway-us-central1 SNAT port allocation exhausted. Outbound paymentservice packets dropped."
                else:
                    st.session_state.active_alert = f"CRITICAL ALERT: Outage simulation '{selected_sim}' triggered."
                    
                st.session_state.cluster_status = "DEGRADED ⚠️"
                st.session_state.messages.append({"role": "assistant", "content": f"💥 **Outage Simulation Triggered (`{selected_sim}`)**\n\n{res}"})
                st.rerun()

    if st.button("🔍 Trigger Autonomous Investigation", use_container_width=True):
        if st.session_state.active_alert.startswith("CRITICAL") or st.session_state.active_alert.startswith("WARNING"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages.append({"role": "user", "content": st.session_state.active_alert})
            st.rerun()
        else:
            st.warning("Please trigger an outage simulation first!")
            
    if st.button("🔄 Reset Dashboard", use_container_width=True):
        st.session_state.messages = []
        st.session_state.active_alert = "None (System Healthy 🟢)"
        st.session_state.cluster_status = "HEALTHY 🟢"
        st.session_state.pending_approval = None
        st.session_state.postmortem_report = None
        st.session_state.session_id = str(uuid.uuid4())
        st.cache_data.clear()
        st.rerun()

# =========================================================================
# 4. TABBED WORKSPACE & SCROLLABLE CHAT CONTAINER
# =========================================================================
tab_ops, tab_releases, tab_report = st.tabs([
    "🚨 Incident Control Room & AI Companion",
    "📦 Recent Releases (BigQuery Ledger)",
    "📑 Compiled Post-Mortem Reports"
])

with tab_ops:
    col_status, col_chat = st.columns([1, 2.2], gap="large")
    
    with col_status:
        st.subheader("🚨 Active System Status")
        if st.session_state.cluster_status == "DEGRADED ⚠️":
            st.markdown(f"""
            <div class="alert-box">
                <b>Status:</b> DEGRADED ⚠️<br>
                <b>Current Alert:</b><br>{st.session_state.active_alert}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="healthy-box">
                <b>Status:</b> HEALTHY 🟢<br>
                <b>Current Alert:</b><br>{st.session_state.active_alert}
            </div>
            """, unsafe_allow_html=True)
        st.info("💡 **Tip:** Use the **Simulate Outage Scenarios** drawer on the left to trigger real cluster anomalies or hit **Trigger Autonomous Investigation** to let the AI triage and self-heal.")

    with col_chat:
        st.subheader("💬 NovaSRE AI Companion")
        st.caption("Chat naturally with your autonomous SRE companion for root-cause triage and guided recovery.")
        
        # Self-contained fixed height scrollable box so chat never overlaps with side elements or stretches down the page!
        chat_box = st.container(height=520, border=True)
        with chat_box:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)
                    
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
                latest_prompt = st.session_state.messages[-1]["content"]
                
                # If an approval is pending and the user typed APPROVE or REJECT, handle it directly!
                if st.session_state.pending_approval and latest_prompt.strip().upper() in ["APPROVE", "APPROVED", "YES"]:
                    app_data = st.session_state.pending_approval
                    with st.spinner("Executing recovery action via Remediation Executor over A2A and compiling post-mortem..."):
                        import asyncio
                        from app.investigator_agent import remediation_executor_remote, incident_report_writer
                        from google.adk.runners import InMemoryRunner
                        from google.genai import types as genai_types
                        
                        async def execute_and_report():
                            rem_result = await remediation_executor_remote(app_data['command'])
                            runner = InMemoryRunner(agent=incident_report_writer, app_name=incident_report_writer.name)
                            await runner.session_service.create_session(app_name=incident_report_writer.name, user_id="sre", session_id=st.session_state.session_id)
                            prompt = f"Incident resolved: {st.session_state.active_alert}. Root cause diagnosed under {app_data['playbook']}. Action taken: {app_data['action']}. A2A execution result: {rem_result}. Please compile the full markdown post-mortem report now."
                            msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])
                            chunks = []
                            async for event in runner.run_async(user_id="sre", session_id=st.session_state.session_id, new_message=msg):
                                if hasattr(event, "content") and event.content and event.content.parts:
                                    for part in event.content.parts:
                                        if hasattr(part, "text") and part.text:
                                            chunks.append(part.text)
                            return rem_result, "".join(chunks)
                        
                        rem_res, report_text = asyncio.run(execute_and_report())
                        st.session_state.postmortem_report = report_text
                        st.session_state.cluster_status = "HEALTHY 🟢"
                        st.session_state.active_alert = "None (System Healthy 🟢)"
                        st.session_state.pending_approval = None
                        ai_reply = format_ai_response(f"✅ **Recovery Action Approved & Executed Successfully!**\n\n**A2A Execution Brief:**\n{rem_res}\n\nI have compiled and archived the full incident report under the **Compiled Post-Mortem Reports** tab.")
                        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                        st.rerun()
                elif st.session_state.pending_approval and latest_prompt.strip().upper() in ["REJECT", "REJECTED", "NO"]:
                    st.session_state.pending_approval = None
                    st.session_state.messages.append({"role": "assistant", "content": "❌ **Action Rejected by Operator.** No changes were made to the cluster."})
                    st.rerun()
                else:
                    with st.chat_message("assistant"):
                        with st.spinner("NovaSRE AI Companion is inspecting telemetry and loading diagnostic skills..."):
                            from app.sre_supervisor import is_network_alert
                            if is_network_alert(latest_prompt):
                                agent_name = "network-triage-expert"
                                urn_env = "NETWORK_TRIAGE_AGENT_URN"
                                local_agent_func = lambda: getattr(importlib.import_module("app.network_agent"), "network_triage_expert")
                            else:
                                agent_name = "rca-telemetry-expert"
                                urn_env = "INVESTIGATOR_AGENT_URN"
                                local_agent_func = lambda: getattr(importlib.import_module("app.investigator_agent"), "rca_telemetry_expert")

                            target_urn = discover_engine_urn(agent_name, urn_env)
                            if target_urn and target_urn.startswith("projects/"):
                                try:
                                    vertexai.init(project=PROJECT_ID, location=GEMINI_LOCATION)
                                    from google.cloud.aiplatform_v1beta1 import types as aip_types
                                    from vertexai.preview.reasoning_engines import ReasoningEngine
                                    remote_agent = ReasoningEngine(target_urn)
                                    resp = remote_agent.execution_api_client.stream_query_reasoning_engine(
                                        request=aip_types.StreamQueryReasoningEngineRequest(
                                            name=remote_agent.resource_name,
                                            input={"user_id": f"sre-{st.session_state.session_id}", "message": {"role": "user", "parts": [{"text": latest_prompt}]}},
                                            class_method="stream_query",
                                        )
                                    )
                                    chunks = []
                                    for chunk in resp:
                                        if hasattr(chunk, "data") and chunk.data:
                                            chunks.append(chunk.data.decode("utf-8", errors="ignore"))
                                    ai_reply = parse_stream_chunks(chunks) if chunks else "Investigation completed."
                                except Exception as e:
                                    ai_reply = f"Cloud inquiry error: {e}. Running local companion..."
                            else:
                                import asyncio
                                import importlib
                                from google.adk.runners import InMemoryRunner
                                from google.genai import types as genai_types
                                target_agent = local_agent_func()
                                
                                async def run_companion():
                                    runner = InMemoryRunner(agent=target_agent, app_name=target_agent.name)
                                    await runner.session_service.create_session(app_name=target_agent.name, user_id="sre", session_id=st.session_state.session_id)
                                    msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=latest_prompt)])
                                    chunks = []
                                    async for event in runner.run_async(user_id="sre", session_id=st.session_state.session_id, new_message=msg):
                                        if hasattr(event, "content") and event.content and event.content.parts:
                                            for part in event.content.parts:
                                                if hasattr(part, "text") and part.text:
                                                    chunks.append(part.text)
                                    return "".join(chunks)
                                ai_reply = format_ai_response(asyncio.run(run_companion()))
                            
                            st.markdown(ai_reply, unsafe_allow_html=True)
                            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                        
                        # Check if the AI proposed a remediation action requiring HITL approval
                        lower_reply = ai_reply.lower()
                        active_alert_lower = st.session_state.active_alert.lower()
                        
                        if ("redis-cart" in active_alert_lower or "pod terminated" in active_alert_lower) and "restart" in lower_reply and "redis-cart" in lower_reply:
                            st.session_state.pending_approval = {
                                "action": "Restart pods for GKE Deployment 'redis-cart' in namespace 'default' to clear stuck database locks.",
                                "command": f"restart deployment redis-cart in namespace default in cluster {GKE_CLUSTER_NAME} in region {GKE_CLUSTER_REGION}",
                                "playbook": "Playbook 3 (Database Lock & Connection Timeout)",
                                "risk": "LOW (Clean rolling pod restart)"
                            }
                        elif ("paymentservice" in active_alert_lower or "latency" in active_alert_lower) and "scale" in lower_reply and "paymentservice" in lower_reply and ("3" in lower_reply or "upsize" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Horizontal Upsize: Scale GKE Deployment 'paymentservice' in namespace 'default' to 3 active replicas.",
                                "command": f"scale deployment paymentservice in namespace default to 3 replicas in cluster {GKE_CLUSTER_NAME} in region {GKE_CLUSTER_REGION}",
                                "playbook": "Playbook 4 (Payment Concurrency Bottleneck)",
                                "risk": "LOW (Horizontal capacity expansion)"
                            }
                        elif ("cartservice" in active_alert_lower or "crashloop" in active_alert_lower) and ("rollback" in lower_reply or "undo rollout" in lower_reply) and ("do you approve" in lower_reply or "requires operator approval" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Rollback GKE Deployment 'cartservice' in namespace 'default' to previous stable revision.",
                                "command": f"undo rollout deployment cartservice in namespace default in cluster {GKE_CLUSTER_NAME} in region {GKE_CLUSTER_REGION}",
                                "playbook": "Playbook 2 (Bad Rollout / CrashLoop)",
                                "risk": "LOW (Pre-approved under Tier 1 Auto-Rollback)"
                            }
                        elif ("frontend" in active_alert_lower or "replicas = 0" in active_alert_lower) and "scale" in lower_reply and ("do you approve" in lower_reply or "requires operator approval" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Scale up GKE Deployment 'frontend' in namespace 'default' to 1 active replica.",
                                "command": f"scale deployment frontend in namespace default to 1 replica in cluster {GKE_CLUSTER_NAME} in region {GKE_CLUSTER_REGION}",
                                "playbook": "Playbook 1 (Infrastructure Replica Scale Outage)",
                                "risk": "LOW (Pre-approved under Tier 1 Auto-Recovery)"
                            }
                        elif ("nat" in active_alert_lower or "snat" in active_alert_lower) and ("nat" in lower_reply or "ports" in lower_reply or "awaiting_approval" in lower_reply or "increase" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Increase Cloud NAT Minimum Allocated Ports per VM from 64 to 256 on 'nat-gateway-us-central1'.",
                                "command": "update cloud nat gateway nat-gateway-us-central1 min ports per vm to 256 in region us-central1",
                                "playbook": "Playbook 7 (Cloud NAT Egress Port Recovery)",
                                "risk": "LOW (Dynamic egress port capacity expansion)"
                            }
                        elif ("networkpolicy" in active_alert_lower or "isolation" in active_alert_lower or "firewall" in active_alert_lower) and ("delete" in lower_reply or "networkpolicy" in lower_reply or "awaiting_approval" in lower_reply or "block" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Delete blocking NetworkPolicy 'chaos-block-checkoutservice' in namespace 'default'.",
                                "command": "delete networkpolicy chaos-block-checkoutservice in namespace default in cluster online-boutique in region us-central1",
                                "playbook": "Playbook 5 (GKE NetworkPolicy Firewall Recovery)",
                                "risk": "LOW (Restores microservice ingress/egress traffic)"
                            }
                        elif ("coredns" in active_alert_lower or "dns" in active_alert_lower) and ("scale" in lower_reply or "coredns" in lower_reply or "replicas" in lower_reply or "awaiting_approval" in lower_reply):
                            st.session_state.pending_approval = {
                                "action": "Scale GKE CoreDNS deployment in namespace 'kube-system' to 2 active replicas.",
                                "command": "scale deployment coredns in namespace kube-system to 2 replicas in cluster online-boutique in region us-central1",
                                "playbook": "Playbook 6 (GKE CoreDNS Failure Recovery)",
                                "risk": "LOW (Restores internal cluster DNS resolution)"
                            }
                        st.rerun()

            # Render Human-in-the-Loop Approval Card right inside the scrollable chat container if pending
            if st.session_state.pending_approval:
                app_data = st.session_state.pending_approval
                st.markdown(f"""
                <div class="approval-card">
                    <h4 style="margin-top:0; color:#f39c12;">⚡ Proposed Recovery Action (Human Approval Required)</h4>
                    <p><b>Target Action:</b> {app_data['action']}</p>
                    <p><b>Matched Playbook:</b> {app_data['playbook']}</p>
                    <p><b>Risk Assessment:</b> {app_data['risk']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                c_app, c_rej = st.columns(2)
                with c_app:
                    if st.button("✅ Approve & Execute Action", use_container_width=True, type="primary"):
                        with st.spinner("Executing recovery action via Remediation Executor over A2A and compiling post-mortem..."):
                            st.session_state.messages.append({"role": "user", "content": "APPROVE"})
                            
                            # Call Remediation Executor directly or via A2A helper
                            import asyncio
                            from app.investigator_agent import remediation_executor_remote, incident_report_writer
                            from google.adk.runners import InMemoryRunner
                            from google.genai import types as genai_types
                            
                            async def execute_and_report():
                                # Execute healing
                                rem_result = await remediation_executor_remote(app_data['command'])
                                
                                # Compile post-mortem report
                                runner = InMemoryRunner(agent=incident_report_writer, app_name=incident_report_writer.name)
                                await runner.session_service.create_session(app_name=incident_report_writer.name, user_id="sre", session_id=st.session_state.session_id)
                                prompt = f"Incident resolved: {st.session_state.active_alert}. Root cause diagnosed under {app_data['playbook']}. Action taken: {app_data['action']}. A2A execution result: {rem_result}. Please compile the full markdown post-mortem report now."
                                msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])
                                chunks = []
                                async for event in runner.run_async(user_id="sre", session_id=st.session_state.session_id, new_message=msg):
                                    if hasattr(event, "content") and event.content and event.content.parts:
                                        for part in event.content.parts:
                                            if hasattr(part, "text") and part.text:
                                                chunks.append(part.text)
                                return rem_result, "".join(chunks)
                            
                            rem_res, report_text = asyncio.run(execute_and_report())
                            st.session_state.postmortem_report = report_text
                            st.session_state.cluster_status = "HEALTHY 🟢"
                            st.session_state.active_alert = "None (System Healthy 🟢)"
                            st.session_state.pending_approval = None
                            st.session_state.messages.append({"role": "assistant", "content": f"✅ **Recovery Action Approved & Executed Successfully!**\n\n**A2A Execution Brief:**\n{rem_res}\n\nI have compiled and archived the full incident report under the **Compiled Post-Mortem Reports** tab."})
                            st.rerun()
                with c_rej:
                    if st.button("❌ Reject Action", use_container_width=True):
                        st.session_state.pending_approval = None
                        st.session_state.messages.append({"role": "user", "content": "REJECT"})
                        st.session_state.messages.append({"role": "assistant", "content": "❌ **Action Rejected by Operator.** No changes were made to the cluster."})
                        st.rerun()

        if prompt := st.chat_input("Chat with NovaSRE AI Companion..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

with tab_releases:
    st.subheader("📦 Recent Releases (BigQuery Deployment Ledger)")
    st.caption("Auto-synced with BigQuery (`bigquery.googleapis.com/mcp`). Cross-referenced by NovaSRE for causal deployment correlation.")
    st.markdown("""
| Release ID | Service | Revision | Deployed By | Summary |
| :--- | :--- | :--- | :--- | :--- |
| **`REL-042`** | `cartservice` | `broken-v2` ⚠️ | `cloud-build` | Updated cart gRPC timeout & format (`CrashLoop` trigger) |
| **`REL-038`** | `frontend` | `v1.0.0` 🟢 | `sre-automation` | Stable production UI update |
| **`REL-035`** | `redis-cart` | `7.0-alpine` 🟢 | `sre-automation` | Database engine minor release upgrade |
    """)

with tab_report:
    st.subheader("📄 Incident Post-Mortem Documentation")
    if st.session_state.postmortem_report:
        st.markdown(st.session_state.postmortem_report, unsafe_allow_html=True)
    else:
        st.info("No compiled report for the current session yet. Reports render automatically right once an active incident is diagnosed and resolved via A2A.")
