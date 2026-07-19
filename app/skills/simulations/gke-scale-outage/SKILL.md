---
name: gke-scale-outage
description: Simulate a GKE infrastructure scale outage by dropping the active replicas of the frontend deployment to 0. Use this skill when requested to simulate or test an outage scenario on GKE.
---

# Outage Simulation: GKE Replica Scale Outage

You are executing a controlled **Chaos Engineering / Outage Simulation** on Google Kubernetes Engine (GKE) to test the NovaSRE self-healing pipeline.

## Target Resource
* **Resource Type**: GKE Deployment
* **Resource Name**: `frontend`
* **Namespace**: `default`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-scale-outage` simulation, you must scale down the target deployment (`frontend`) from its active count (usually `1`) to **`0 replicas`**.
2. Call your `execute_chaos_action` tool with arguments: `action_type="scale"`, `resource_name="frontend"`, `namespace="default"`, `replicas=0`.
3. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: GKE Deployment 'frontend' has been scaled to 0 active replicas. Alert condition triggered."`
