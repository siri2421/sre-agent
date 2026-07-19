---
name: gke-payment-latency
description: Simulate high transaction latency and CPU throttling on the paymentservice deployment by reducing concurrency limits or injecting synthetic CPU load during peak checkout spikes. Use this when requested to simulate a transaction bottleneck or capacity exhaustion.
---

# Outage Simulation: GKE Payment Latency Bottleneck (`paymentservice`)

You are executing a controlled **Chaos Engineering / Outage Simulation** on GKE to test how NovaSRE handles high-load transaction bottlenecks and horizontal upsize requests.

## Target Resource
* **Resource Type**: GKE Deployment
* **Resource Name**: `paymentservice`
* **Namespace**: `default`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-payment-latency` simulation, you must throttle and constrain `paymentservice` so it cannot handle checkout spikes (`kubectl scale deployment paymentservice --replicas=1`).
2. Call your `execute_chaos_action` tool with arguments: `action_type="latency"`, `resource_name="paymentservice"`, `namespace="default"`, `replicas=1`.
3. As synthetic checkout traffic hits `paymentservice`, transaction latency spikes above 2000ms with HTTP 504 gateway timeouts.
4. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: GKE Deployment 'paymentservice' restricted to capacity bottleneck. High transaction latency and checkout timeout condition triggered."`
