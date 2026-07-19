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
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from dotenv import load_dotenv

# Load environment variables & trigger centralized runtime patches from config
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.config import (
    PROJECT_ID,
    GEMINI_MODEL,
    GKE_CLUSTER_NAME,
    GKE_CLUSTER_REGION,
    GKE_MCP_SERVER,
    get_mcp_toolset,
    LazyToolset
)

# =========================================================================
# AGENT: The Secure Healing Worker (remediation_executor)
# =========================================================================
_REMEDIATION_INSTRUCTION = f"""
You are the GKE Remediation Executor (remediation_executor), an elite GKE engineering expert.

**Persona:** Highly disciplined, operationally focused, and precise. Emojis for dry armor. 🤖🛡️
**Target Environment:**
* Project ID: `{PROJECT_ID}`
* GKE Cluster Name: `{GKE_CLUSTER_NAME}`
* Location/Region: `{GKE_CLUSTER_REGION}`
* Default Namespace: `default`

**Your Job:**
Given an approved action and target GKE resource, execute the healing playbook safely and validate system recovery using your GKE OneMCP tools against `{GKE_CLUSTER_NAME}` in `{GKE_CLUSTER_REGION}`.

**Operating Principles:**
1. **Strict HITL Compliance:** You operate under strict Human-in-the-Loop gating. You MUST ONLY execute the action that has been explicitly approved in your prompt. Never improvise.
2. **Safety & Validation:** After executing a GKE pod restart (`delete_k8s_pod`) or rollback, you must query GKE pod status to verify that the replacement pod has successfully reached a stable `Running` and `Ready` state in target cluster `{GKE_CLUSTER_NAME}`.
3. **Output Format:** Return a concise, structured brief confirming the action taken, the resource targeted, and the health status of the GKE resource (e.g., "GKE Deployment frontend successfully restarted and verified healthy").
"""

_remediation_tools = [
    LazyToolset(lambda: get_mcp_toolset(GKE_MCP_SERVER))
]

remediation_executor = Agent(
    name="remediation_executor",
    model=Gemini(
        model=GEMINI_MODEL,
    ),
    instruction=_REMEDIATION_INSTRUCTION,
    tools=_remediation_tools,
)

# =========================================================================
# CENTRALIZED A2A AGENT DECLARATION (Vertex AI A2aAgent Template)
# =========================================================================
from vertexai.preview.reasoning_engines import A2aAgent
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.runners import Runner

def _get_remediation_agent_card():
    from a2a import types as a2a_types
    return a2a_types.AgentCard(
        name="remediation-executor",
        description="The GKE Remediation Executor agent. Executes approved GKE pod restarts and rollbacks.",
        version="1.0",
        url="https://dummy.com",
        capabilities=a2a_types.AgentCapabilities(),
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[],
        preferredTransport="HTTP+JSON",
    )

def build_remediation_executor():
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService

    runner = Runner(
        app_name="remediation-executor",
        agent=remediation_executor,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )
    return A2aAgentExecutor(runner=runner)

# Expose the pure A2A Agent template for Vertex AI Agent Engine deployment so Agent Registry registers Agent Type: A2A
agent_engine = A2aAgent(
    agent_card=_get_remediation_agent_card(),
    agent_executor_builder=build_remediation_executor
)
