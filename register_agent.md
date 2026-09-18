# 🛡️ NovaSRE — Agent Registration & Testing Guide

This guide provides generalized, step-by-step instructions for registering and verifying the **`outage-simulator`** and **`rca-telemetry-expert`** agents in your **Gemini Enterprise** web application across any Google Cloud project.

---

## 📋 Dynamic Component & Environment Discovery

Before beginning registration, extract your deployment's active live identifiers from Google Cloud:

```bash
# Set your target project and region
export GCP_PROJECT_ID=$(gcloud config get-value project)
export GCP_REGION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
export GCP_PROJECT_NUM=$(gcloud projects describe "$GCP_PROJECT_ID" --format="value(projectNumber)")

# Extract active Reasoning Engine URNs from Vertex AI
export SIM_URN=$(curl -4 -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${GCP_REGION}-aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_NUM}/locations/${GCP_REGION}/reasoningEngines" \
  | grep -B 1 '"displayName": "outage-simulator"' | grep 'projects/' | grep -o 'projects/[^"]*')

export RCA_URN=$(curl -4 -s -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${GCP_REGION}-aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_NUM}/locations/${GCP_REGION}/reasoningEngines" \
  | grep -B 1 '"displayName": "rca-telemetry-expert"' | grep 'projects/' | grep -o 'projects/[^"]*')

export RCA_A2A_URL="https://${GCP_REGION}-aiplatform.googleapis.com/v1beta1/${RCA_URN}/a2a"

echo "========================================================"
echo "GCP Project ID:                     $GCP_PROJECT_ID"
echo "GCP Project Number:                 $GCP_PROJECT_NUM"
echo "GCP Region:                         $GCP_REGION"
echo "Outage Simulator URN:               $SIM_URN"
echo "RCA Telemetry Expert URN:           $RCA_URN"
echo "RCA Telemetry Expert A2A URL:       $RCA_A2A_URL"
echo "OAuth Redirect URI:                 https://vertexaisearch.cloud.google.com/oauth-redirect"
echo "========================================================"
```

### Component Reference Matrix

| Component | Description | Format / Default |
| :--- | :--- | :--- |
| **GCP Project ID** | Target Google Cloud Project | `<YOUR_PROJECT_ID>` (e.g. `sre-hitl`) |
| **GCP Project Number** | Numerical identifier of your project | `<YOUR_PROJECT_NUM>` (e.g. `377676639711`) |
| **GCP Region** | Region hosting Vertex AI Reasoning Engines | `<LOCATION>` (e.g. `us-central1`) |
| **Gemini Enterprise Web App** | Web application console instance | `https://vertexaisearch.cloud.google.com/home/cid/<TENANT_ID>` |
| **OAuth 2.0 Redirect URI** | Authorized redirect endpoint for 3LO | `https://vertexaisearch.cloud.google.com/oauth-redirect` |
| **Outage Simulator Engine URN** | Serverless runtime URN for Chaos Engine | `projects/<PROJECT_NUM>/locations/<REGION>/reasoningEngines/<SIM_ENGINE_ID>` |
| **RCA Telemetry Expert URN** | Serverless runtime URN for Diagnostician | `projects/<PROJECT_NUM>/locations/<REGION>/reasoningEngines/<RCA_ENGINE_ID>` |
| **RCA Telemetry Expert A2A URL** | Direct HTTP+JSON A2A protocol endpoint | `https://<REGION>-aiplatform.googleapis.com/v1beta1/<RCA_URN>/a2a` |

---

## 🔑 Step 1: Create OAuth 2.0 Web Client Credentials

The `rca-telemetry-expert` agent executes operations on behalf of the signed-in operator using Three-Legged OAuth (3LO).

1. Open the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials) and ensure your target project is selected.
2. If prompted to configure the **OAuth consent screen**:
   - Choose **Internal** (scoped to your Google Workspace organization) and click **Create**.
   - Set **App name**: `NovaSRE Assistant`.
   - Provide your support and developer contact email address.
   - Click **Save and Continue** through the remaining steps.
3. In the **Credentials** page:
   - Click **+ Create Credentials** → **OAuth client ID**.
   - Set **Application type**: **Web application**.
   - Set **Name**: `Gemini Enterprise SRE Client`.
   - Under **Authorized redirect URIs**, click **+ ADD URI**.
   - Paste:
     ```text
     https://vertexaisearch.cloud.google.com/oauth-redirect
     ```
   - Click **Create**.
4. Copy and securely store the generated:
   - **Client ID** (e.g., `<PROJECT_NUMBER>-<HASH>.apps.googleusercontent.com`)
   - **Client Secret** (e.g., `GOCSPX-<SECRET>`)

---

## 🤖 Step 2: Register the Outage Simulator in Gemini Enterprise

The Outage Simulator is registered as a custom agent via the serverless Vertex AI Reasoning Engine runtime:

1. Open your Gemini Enterprise administrative console or Agent Gallery.
2. Click **Add Custom Agent** (or **Create Agent**).
3. Select **Agent Runtime** (or **Vertex AI Reasoning Engine**).
4. Enter the registration parameters:
   - **Agent Name**: `outage-simulator`
   - **Display Name**: `NovaSRE Chaos Engine`
   - **Reasoning Engine Resource Name / URN**: Use your resolved `$SIM_URN`:
     ```text
     projects/<GCP_PROJECT_NUM>/locations/<GCP_REGION>/reasoningEngines/<SIM_ENGINE_ID>
     ```
   - **Description**:
     ```text
     NovaSRE Chaos Engine. Injects controlled failure modes (pod crashes, replica downscales, bad rollouts, DNS outages, NetworkPolicy isolation, Cloud NAT port drops, and broken service routing) into the target GKE cluster for demonstration and testing.
     ```
5. Click **Save / Register**.

---

## 🩺 Step 3: Register the RCA Telemetry Expert in Gemini Enterprise

The RCA Telemetry Expert is registered as a **Custom A2A Agent** with interactive A2UI support:

1. In the Gemini Enterprise Console, click **Add Custom Agent** → **Agent-to-Agent (A2A)**.
2. In the **OAuth 2.0 Authentication** section, provide:
   - **Client ID**: `<YOUR_CLIENT_ID_FROM_STEP_1>`
   - **Client Secret**: `<YOUR_CLIENT_SECRET_FROM_STEP_1>`
   - **Authorization URL**:
     ```text
     https://accounts.google.com/o/oauth2/auth?access_type=offline&prompt=consent
     ```
   - **Token URL**:
     ```text
     https://oauth2.googleapis.com/token
     ```
   - **Scope**:
     ```text
     https://www.googleapis.com/auth/cloud-platform
     ```
3. In the **Agent Card** JSON field, paste the following specification (substituting your resolved `$RCA_A2A_URL`):

```json
{
  "name": "rca-telemetry-expert",
  "description": "The SRE RCA Telemetry Expert agent. Performs root-cause analysis, cross-correlates observability signals, and delegates GKE remediation under HITL gating.",
  "version": "1.0",
  "protocolVersion": "0.3.0",
  "url": "https://<GCP_REGION>-aiplatform.googleapis.com/v1beta1/projects/<GCP_PROJECT_NUM>/locations/<GCP_REGION>/reasoningEngines/<RCA_ENGINE_ID>/a2a",
  "capabilities": {
    "streaming": true,
    "extensions": [
      {
        "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8",
        "description": "Provides agent driven UI using the A2UI JSON format."
      }
    ]
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [],
  "preferredTransport": "HTTP+JSON"
}
```
4. Click **Save / Register**.

---

## 🧪 Step 4: Testing & Verification in the Web App

1. Launch your Gemini Enterprise Web App.
2. Log in using your authorized organizational account.

### Test A: Trigger Chaos Engineering Outage
In the Gemini Enterprise prompt:
```text
@outage-simulator Run the gke-scale-outage simulation — scale the frontend deployment in namespace default to 0 replicas.
```
* **Expected Outcome**: The Chaos Engine invokes GKE and downscales `frontend` to 0 replicas, causing HTTP 503 errors on the store.

### Test B: Trigger Autonomous RCA & HITL Remediation
In the Gemini Enterprise prompt:
```text
@rca-telemetry-expert The online-boutique store is down and returning HTTP 503 errors. Investigate root cause and remediate.
```
* **Expected Outcome**:
  1. The RCA agent triages Cloud Logging, Cloud Monitoring, and GKE workload status via OneMCP.
  2. Diagnoses that `frontend` replicas were dropped to 0.
  3. **Tier 1 (Auto-Recovery)**: Autonomously delegates to `remediation-executor` over A2A and restores the service.
  4. **Tier 2 (Gated HITL Approval)**: Renders an interactive **A2UI widget** inline with an **`[ ✅ Approve & Execute ]`** button. Upon clicking approve, it executes the remediation via PAM JIT elevation and confirms recovery.
