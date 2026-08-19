---
name: gke-network-firewall-block
description: Simulate a GKE network traffic isolation / firewall block by creating a restrictive NetworkPolicy that drops ingress and egress traffic on target microservice (e.g. checkoutservice or frontend).
---

# Outage Simulation: GKE Network Traffic Block (NetworkPolicy / Firewall Drop)

You are executing a controlled **Chaos Engineering / Network Outage Simulation** on Google Kubernetes Engine (GKE) to test the NovaSRE network triaging pipeline.

## Target Resource
* **Resource Type**: GKE NetworkPolicy / Workload
* **Resource Name**: `checkoutservice` (or `frontend`)
* **Namespace**: `default`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-network-firewall-block` simulation, apply a restrictive NetworkPolicy `chaos-block-checkoutservice` dropping all ingress and egress packets for the target pod.
2. Call your `execute_chaos_action` tool with arguments: `action_type="network_block"`, `resource_name="checkoutservice"`, `namespace="default"`.
3. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: NetworkPolicy 'chaos-block-checkoutservice' applied in namespace 'default'. Traffic to checkoutservice isolated."`
