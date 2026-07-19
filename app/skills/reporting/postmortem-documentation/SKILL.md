---
name: postmortem-documentation
description: Safely execute approved infrastructure remediation actions (pod restarts, deployment rollbacks) on GKE, validate post-action system health, and write post-mortem reports to Cloud Storage (GCS). Use this skill whenever you need to execute a mutating healing action or compile/archive incident documentation. Covers the use of GKE write tools and GCS storage tools.
---

# GCP Remediation and Documentation skill

You are executing **mutating infrastructure actions** and **archiving post-incident documentation** through your write-scoped GKE and GCS MCP toolsets. This skill teaches you how to execute healing playbooks safely and document the outcomes.

## Tools you have

| Tool | When to use |
|---|---|
| `delete_k8s_pod` | **Primary Pod Restart.** Deletes a GKE pod by name and namespace. GKE will automatically spin up a fresh replacement. |
| `rollback_deployment` | Roll back a GKE deployment to its previous stable revision if a bad container image was rolled out. |
| `list_k8s_pods` | Query GKE pod states to verify that replacement pods have successfully reached `Running` and `Ready` states. |
| `write_gcs_file` | Save the final Markdown post-mortem report to a secure Cloud Storage bucket. |

## Hard rules for Remediation

1. **HITL Gate Compliance**: You MUST ONLY execute actions that have been explicitly approved by the human operator in your prompt context. NEVER improvise a mutating action that was not part of the approved payload.
2. **Target Validation**: Always double-check the namespace and resource name of the target before executing `delete_k8s_pod`. A typo can crash unrelated production services.
3. **Post-Action Verification**: After calling `delete_k8s_pod`, you are NOT finished. You must wait and query `list_k8s_pods` at least twice (with a 15-second sleep) to verify that:
   - The old pod is terminated.
   - A new pod has successfully reached `STATUS=Running` and `READY=1/1`.
4. **Failure Escalation**: If the new pod enters a `CrashLoopBackOff` or fails to become ready within 60 seconds, immediately halt, log the failure, and alert the operator. Do NOT attempt a second deletion.

## Hard rules for Post-Mortem Documentation

1. **Standard Template**: Every post-mortem report must be written in clean Markdown and contain the following sections:
   - `# Incident Post-Mortem Report`
   - `## Executive Summary` (Incident ID, Alert, Status: RESOLVED/FAILED, Timestamps)
   - `## Root Cause Analysis (RCA)` (Detailed description of what failed and why)
   - `## Remediation & Recovery` (Actions executed, timestamps, and validation outcomes)
   - `## Technical Timeline` (Step-by-step log of the incident lifecycle)
2. **Naming Convention**: Save the report to GCS as `gs://<BUCKET_NAME>/reports/post_mortem_<INCIDENT_ID>.md`. Use the unique incident UUID in the filename.
3. **Secure Links**: Provide the operator with the direct `gs://` URI of the archived report in your final output.
