---
name: gke-service-routing-break
description: Simulate a GKE service routing failure by breaking the selector on the checkoutservice Service, disabling traffic routing to pods.
---

# Outage Simulation: GKE Service Routing Break

You are executing a controlled **Chaos Engineering / Network Outage Simulation** on GKE to test the NovaSRE network triaging pipeline.

## Target Resource
* **Resource Type**: GKE Service / Traffic Routing
* **Resource Name**: `checkoutservice`
* **Namespace**: `default`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-service-routing-break` simulation, apply a broken selector to the service to disable traffic routing to pods.
2. Call your `execute_chaos_action` tool with arguments: `action_type="service_routing"`, `resource_name="checkoutservice"`, `namespace="default"`.
3. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: Service selector modified on checkoutservice in default namespace. Traffic routing disabled."`
