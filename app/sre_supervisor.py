import os
import sys
import time
import json
import argparse
import uuid
import asyncio
import threading
import uvicorn
from fastapi import FastAPI, HTTPException
from google.genai import types
from google.adk.runners import InMemoryRunner

# Import our ADK Agents
from app.investigator_agent import rca_telemetry_expert, incident_report_writer
from app.network_agent import network_triage_expert
from app.remediation_agent import remediation_executor
from app.config import PROJECT_ID

# ==========================================
# 1. CENTRALIZED HITL SESSION STORE & FASTAPI
# ==========================================
web_app = FastAPI(title="SRE Supervisor HITL Gateway")
session_store = {}

@web_app.post("/callback/{session_id}")
async def callback(session_id: str, decision: str):
    """Receive the operator's approval or rejection callback."""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    normalized_decision = decision.upper()
    if normalized_decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED")
    
    session_store[session_id]["status"] = normalized_decision
    return {
        "status": "success",
        "session_id": session_id,
        "decision": normalized_decision
    }

def start_hitl_server():
    """Runs the FastAPI server in a background thread."""
    uvicorn.run(web_app, host="127.0.0.1", port=8000, log_level="error")

# ==========================================
# 2. BEAUTIFUL SRE LOGGING UTILITY
# ==========================================
def log_step(agent: str, message: str, color: str = "36"):
    """Prints a styled, colorized log message showing which agent is acting."""
    # Colors: 36=Cyan (Supervisor), 35=Magenta (RCA), 32=Green (Remediation), 33=Yellow (Reporting), 31=Red (Alert/Gate)
    print(f"\033[1;{color}m[{agent.upper()}]\033[0m {message}")

def is_network_alert(alert_payload: str) -> bool:
    """Helper to detect if an incoming alert involves Google Cloud networking or GKE network layer issues."""
    network_keywords = [
        "network", "vpc", "firewall", "nat", "dns", "connectivity",
        "ingress", "egress", "rtt", "latency", "packet loss", "packet drop",
        "cloud armor", "load balancer", "gateway api", "502", "503", "504",
        "connection refused", "connection reset", "timeout", "route", "subnet"
    ]
    payload_lower = alert_payload.lower()
    return any(keyword in payload_lower for keyword in network_keywords)

# ==========================================
# 3. RUNNER HELPER FOR STREAMING CONSUMPTION
# ==========================================
async def run_agent_locally(agent, prompt: str, session_id: str, user_id: str = "sre-operator") -> str:
    """Helper to instantiate an InMemoryRunner, create a session, and run the agent to collect its output."""
    runner = InMemoryRunner(agent=agent)
    
    # Explicitly create the session first in the runner's session service
    await runner.session_service.create_session(
        app_name=runner.app_name or agent.name,
        user_id=user_id,
        session_id=session_id
    )
    
    # Format the prompt into ADK Content
    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
    
    chunks = []
    # Consume the streaming async generator
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    chunks.append(part.text)
                    
    return "".join(chunks)

# ==========================================
# 4. CORE ASYNC ORCHESTRATION WORKFLOW
# ==========================================
async def run_sre_pipeline(alert_payload: str):
    session_id = str(uuid.uuid4())
    print("=" * 75)
    print(f"STARTING SRE SUPERVISOR SESSION: {session_id}")
    print(f"Incoming Alert: '{alert_payload}'")
    print(f"Target Project:  '{PROJECT_ID}'")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # STEP 1: TELEMETRY DIAGNOSTICS & CONDITIONAL ROUTING
    # -------------------------------------------------------------------------
    if is_network_alert(alert_payload):
        target_agent = network_triage_expert
        agent_name = "network_triage_expert"
        log_step("Supervisor", "🌐 Network domain anomaly detected. Conditionally routing alert to network_triage_expert...", "36")
    else:
        target_agent = rca_telemetry_expert
        agent_name = "rca_telemetry_expert"
        log_step("Supervisor", "⚙️ Workload/Application domain anomaly detected. Routing alert to rca_telemetry_expert...", "36")
    
    rca_prompt = f"""
    Investigate this GKE/GCP alert in project {PROJECT_ID}:
    '{alert_payload}'
    
    Query your logging, monitoring, tracing, and network tools, find the root cause, and return your SRE JSON facts packet.
    """
    
    # Run the diagnostician and wait for results
    rca_response = await run_agent_locally(target_agent, rca_prompt, f"rca-{session_id}")

    
    # Parse the structured SRE facts packet
    try:
        import re
        json_match = re.search(r"```json\s*(.*?)\s*```", rca_response, re.DOTALL)
        if json_match:
            cleaned_response = json_match.group(1)
        else:
            cleaned_response = rca_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        rca_data = json.loads(cleaned_response)
        log_step(agent_name, f"Diagnostics complete. Isolated root cause:\n{json.dumps(rca_data, indent=2)}", "35")
    except Exception as e:
        log_step("Supervisor", f"CRITICAL: Failed to parse RCA Agent response as JSON. Raw response:\n{rca_response}", "31")
        return

    # Extract recommendation and status details
    remediation_status = rca_data.get("remediation_status", "NOT_REQUIRED").upper()
    action = rca_data.get("recommended_action", "NONE").upper()
    resource = rca_data.get("target_resource", "")
    root_cause = rca_data.get("root_cause", "")

    if action == "NONE":
        log_step("Supervisor", "No mutating action recommended. Skipping remediation. Incident Closed.", "32")
        return

    # If the RCA Agent already successfully executed the remediation (Tier 1 Playbook auto-recovery)
    if remediation_status == "SUCCESS":
        log_step("Supervisor", f"Auto-remediation '{action}' was ALREADY executed successfully in the cloud via pre-approved Tier 1 Playbook on resource: {resource}.", "32")
        log_step("Supervisor", "Bypassing Human-in-the-Loop Safety Gate (Pre-approved Auto-Recovery).", "32")
        remediation_response = f"Automated recovery action '{action}' was successfully executed and verified on {resource} via pre-approved Tier 1 SRE Playbook."
    else:
        # -------------------------------------------------------------------------
        # STEP 2: HUMAN-IN-THE-LOOP SAFETY GATE (Tier 2/3 Fallback)
        # -------------------------------------------------------------------------
        log_step("Supervisor", f"CRITICAL: Mutating action '{action}' recommended on resource: {resource}", "31")
        
        # Register the session in our local store
        session_store[session_id] = {
            "status": "AWAITING_APPROVAL",
            "action": action,
            "resource": resource,
            "rca_details": rca_data
        }

        print(f"\n\033[1;31m>>> 🚨 HUMAN-IN-THE-LOOP SAFETY GATE ACTIVE 🚨 <<<\033[0m")
        print(f"The SRE Supervisor has paused execution to prevent unauthorized infrastructure modification.")
        print(f"To APPROVE this remediation, execute:")
        print(f"   \033[1;32mcurl -X POST 'http://127.0.0.1:8000/callback/{session_id}?decision=APPROVED'\033[0m")
        print(f"To REJECT this remediation, execute:")
        print(f"   \033[1;31mcurl -X POST 'http://127.0.0.1:8000/callback/{session_id}?decision=REJECTED'\033[0m\n")

        log_step("Supervisor", "Suspending execution. Awaiting operator callback...", "31")
        
        # Polling loop waiting for the FastAPI background thread to receive the operator decision
        decision = None
        while True:
            status = session_store[session_id]["status"]
            if status == "APPROVED":
                decision = True
                break
            elif status == "REJECTED":
                decision = False
                break
            sys.stdout.write("\033[1;31m.\033[0m")
            sys.stdout.flush()
            await asyncio.sleep(2.0)
        print("\n")

        if not decision:
            log_step("Supervisor", "Remediation REJECTED by operator. Bypassing execution. Incident Closed.", "31")
            return

        # -------------------------------------------------------------------------
        # STEP 3: SECURE REMEDIATION (remediation_executor - A2A SIMULATION)
        # -------------------------------------------------------------------------
        log_step("Supervisor", "Remediation APPROVED. Invoking remediation_executor via secure A2A...", "36")
        
        remediation_prompt = f"""
        The operator has APPROVED the following remediation:
        - Action: {action}
        - Target Resource: {resource}
        - Root Cause: {root_cause}
        
        Please execute this action using your GKE tools, verify GKE pod recovery, and return your execution outcomes.
        """
        
        remediation_response = await run_agent_locally(remediation_executor, remediation_prompt, f"rem-{session_id}")
        log_step("remediation_executor", f"Remediation and validation cycle complete:\n{remediation_response}", "32")

    # -------------------------------------------------------------------------
    # STEP 4: INCIDENT REPORTING (incident_report_writer - SUBAGENT COLLABORATION)
    # -------------------------------------------------------------------------
    log_step("Supervisor", "Invoking incident_report_writer as reporting subagent...", "36")
    
    reporting_prompt = f"""
    An incident occurred and has been successfully remediated. Please compile the post-mortem report and archive it to GCS.
    
    **Incident Details:**
    - Alert: {alert_payload}
    - Root Cause: {root_cause}
    - Action Executed: {action} on {resource}
    - Execution Outcomes: {remediation_response}
    
    Write the Markdown report and save it to GCS.
    """
    
    reporting_response = await run_agent_locally(incident_report_writer, reporting_prompt, f"rep-{session_id}")
    log_step("incident_report_writer", f"Post-mortem report compiled and archived:\n{reporting_response}", "33")

    print("=" * 75)
    print("SRE SUPERVISOR SESSION COMPLETED SUCCESSFULLY.")
    print("=" * 75)

# ==========================================
# 5. MAIN ENTRY POINT
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Extensible SRE Supervisor Agent (ADK 2.0)")
    parser.add_argument(
        "--alert", 
        type=str, 
        default="GKE Pod frontend-d47bbd964-4z82r is crashing with OOMKilled in namespace default",
        help="The incoming alert string to process."
    )
    args = parser.parse_args()

    # 1. Start the FastAPI HITL server in a background thread
    server_thread = threading.Thread(target=start_hitl_server, daemon=True)
    server_thread.start()
    time.sleep(1.0) # Allow server to bind

    # 2. Run the async orchestration pipeline
    asyncio.run(run_sre_pipeline(args.alert))

if __name__ == "__main__":
    main()
