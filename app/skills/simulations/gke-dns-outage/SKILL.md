---
name: gke-dns-outage
description: Simulate a cluster-wide GKE CoreDNS domain resolution outage by scaling CoreDNS in namespace kube-system to 0 replicas, causing cluster.local resolution timeouts across online-boutique microservices.
---

# Outage Simulation: GKE CoreDNS Resolution Outage

You are executing a controlled **Chaos Engineering / Network Outage Simulation** on Google Kubernetes Engine (GKE) to test the NovaSRE network triaging pipeline.

## Target Resource
* **Resource Type**: GKE Deployment (Cluster DNS)
* **Resource Name**: `coredns` (or `kube-dns`)
* **Namespace**: `kube-system`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-dns-outage` simulation, scale down the Cluster DNS deployment (`coredns` / `kube-dns`) in namespace `kube-system` to **`0 replicas`**.
2. Call your `execute_chaos_action` tool with arguments: `action_type="scale"`, `resource_name="coredns"`, `namespace="kube-system"`, `replicas=0`.
3. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: GKE CoreDNS deployment in namespace 'kube-system' scaled to 0 replicas. DNS resolution timeout anomaly triggered."`
