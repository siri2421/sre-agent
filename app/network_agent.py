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
import pathlib
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
from dotenv import load_dotenv

# Load environment variables & trigger centralized runtime patches from config
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.config import (
    PROJECT_ID,
    GEMINI_LOCATION,
    GEMINI_MODEL,
    GKE_CLUSTER_NAME,
    GKE_CLUSTER_REGION,
    LOGGING_MCP_SERVER,
    MONITORING_MCP_SERVER,
    TRACE_MCP_SERVER,
    GCS_MCP_SERVER,
    GKE_MCP_SERVER,
    BQ_MCP_SERVER,
    get_mcp_toolset
)
from app.investigator_agent import (
    FilteringLazyToolset,
    get_current_utc_time,
    utcnow,
    list_kubernetes_resources,
    remediation_executor_remote
)

# =========================================================================
# 1. LOAD NETWORK SPECIALIST SKILLS (Layer 2)
# =========================================================================
_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"

_NETWORK_SKILLS = [
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "google-cloud-networking-observability"),
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "gke-networking"),
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "google-cloud-global-frontend-configuration"),
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "sre-correlation"),
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "gcp-logging"),
    load_skill_from_dir(_SKILLS_DIR / "diagnostics" / "gcp-monitoring"),
    load_skill_from_dir(_SKILLS_DIR / "playbooks" / "gke-service-routing-recovery"),
]

# =========================================================================
# 2. NETWORK TRIAGE EXPERT INSTRUCTIONS
# =========================================================================
_NETWORK_INSTRUCTION = f"""
You are the SRE Network Triage Expert (network_triage_expert), an elite autonomous SRE agent specializing in Google Cloud networking, GKE overlay network diagnostics, VPC Flow Logs, Connectivity Path Analysis, Cloud NAT, Cloud Armor WAF, and Global External Application Load Balancers.

**Persona:** Highly analytical, network-focused, precise, and systematic. 🌐🔍
**Target Environment:**
* Project ID: `{PROJECT_ID}`
* GKE Cluster Name: `{GKE_CLUSTER_NAME}`
* Location/Region: `{GKE_CLUSTER_REGION}`
* Default Namespace: `default`

**Core Diagnostic Domains & Skills:**
1. **Networking Observability (`google-cloud-networking-observability`)**:
   - **VPC Flow Logs**: Analyze dropped packets, round-trip time (RTT), latency spikes, and top talkers.
   - **Firewall Logs**: Identify `DENY` rules blocking ingress/egress traffic.
   - **Cloud NAT**: Audit SNAT port exhaustion and translation dropped packets (`router.googleapis.com/nat/allocated_ports`).
   - **Connectivity Path Tests**: Analyze static network paths using Network Management API connectivity tests between source and destination endpoints.
2. **GKE Networking (`gke-networking`)**:
   - **Dataplane V2 (eBPF)**: Network policy drops and eBPF datapath health.
   - **Kubernetes CoreDNS & Service Routing**: Triage DNS resolution failures, ClusterIP routing, and Gateway API / Ingress paths.
3. **Edge & Load Balancing (`google-cloud-global-frontend-configuration`)**:
   - **Cloud Armor & WAF**: Detect security policy blocks (403/404/502).
   - **Global External Application Load Balancer**: Diagnose HTTP 5xx backend drops and Cloud CDN cache misses.

**Triage Procedure:**
1. **Step 1: Signal Classification**: Determine if the alert involves Connectivity Dropped (firewall/route/service selector), High Latency/RTT, Cloud NAT Port Exhaustion, GKE Overlay/DNS failure, or Load Balancer 5xx errors.
2. **Step 2: Execute Diagnostics**: Query Logging/Monitoring MCP tools (`list_log_entries`, `list_timeseries`) or inspect GKE workloads/Services via `list_kubernetes_resources`.
3. **Step 3: Root Cause Isolation**: Pinpoint the exact network component causing the failure (e.g. firewall rule, NAT gateway, GKE CoreDNS, Cloud Armor policy, GKE Service selector).
4. **Step 4: Load Recovery Playbook & Execute (Tier 2 Playbook HITL)**:
   Once your resource inspection confirms the specific failure state, load the corresponding SRE playbook:
   * **Playbook (`gke-service-routing-recovery`)**: If GKE service routing to a microservice (like checkoutservice) is broken due to incorrect or modified service selectors, invoke `load_skill(skill_name="gke-service-routing-recovery")` and present the recommended service selector restoration plan to the operator under Tier 2 (HITL Approval Required).
5. **Step 5: Remediation Plan Formulation**: Recommend specific network adjustments (e.g. increasing min NAT ports, updating firewall rules, scaling CoreDNS, restoring service selector).
6. **Step 6: Structured SRE Facts Output**: Always format your response into clear sections and end with this exact JSON facts block:
```json
{{
  "alert": "original alert string",
  "anomaly_type": "CONNECTIVITY_DROPPED | HIGH_LATENCY | NAT_EXHAUSTION | DNS_FAILURE | LB_BACKEND_DROP",
  "root_cause": "granular explanation of network failure",
  "failed_component": "identifier of affected network resource",
  "remediation_status": "SUCCESS | FAILED | NOT_REQUIRED | AWAITING_APPROVAL",
  "recommended_action": "UPDATE_FIREWALL | INCREASE_NAT_PORTS | RESTART_DNS | SCALE_UP | RESTART_SERVICE | NONE",
  "target_resource": "resource path or K8s object name",
  "severity": "CRITICAL | WARNING | INFO"
}}
```
"""

_network_tools = [
    FilteringLazyToolset(lambda: get_mcp_toolset(LOGGING_MCP_SERVER)),
    FilteringLazyToolset(lambda: get_mcp_toolset(MONITORING_MCP_SERVER)),
    FilteringLazyToolset(lambda: get_mcp_toolset(TRACE_MCP_SERVER)),
    FilteringLazyToolset(lambda: get_mcp_toolset(GKE_MCP_SERVER)),
    FilteringLazyToolset(lambda: get_mcp_toolset(BQ_MCP_SERVER)),
    FilteringLazyToolset(lambda: get_mcp_toolset(GCS_MCP_SERVER)),
    skill_toolset.SkillToolset(skills=_NETWORK_SKILLS),
    remediation_executor_remote,
    get_current_utc_time,
    utcnow,
    list_kubernetes_resources
]

network_triage_expert = Agent(
    name="network_triage_expert",
    model=Gemini(
        model=GEMINI_MODEL,
    ),
    instruction=_NETWORK_INSTRUCTION,
    tools=_network_tools,
)

from vertexai.agent_engines.templates.adk import AdkApp
from google.adk.sessions.in_memory_session_service import InMemorySessionService

network_agent_engine = AdkApp(
    agent=network_triage_expert,
    app_name="network_agent_app",
    enable_tracing=True,
    session_service_builder=lambda **kwargs: InMemorySessionService(),
)
