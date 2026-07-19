---
name: gke-pod-crash
description: Simulate a GKE database lock and pod crash on the redis-cart deployment by deleting active pods and injecting an invalid environment configuration or stuck connection state. Use this when requested to simulate a database connection drop or stuck pod state.
---

# Outage Simulation: GKE Database Lock (`redis-cart`)

You are executing a controlled **Chaos Engineering / Outage Simulation** on GKE to test how NovaSRE handles stuck database connection pools and pod crashes.

## Target Resource
* **Resource Type**: GKE Deployment
* **Resource Name**: `redis-cart`
* **Namespace**: `default`
* **Cluster**: `online-boutique`

## Simulation Instructions
1. When asked to execute the `gke-pod-crash` simulation, you must terminate the active pods of `redis-cart` (`kubectl delete pod -l app=redis-cart`).
2. Call your `execute_chaos_action` tool with arguments: `action_type="crash"`, `resource_name="redis-cart"`, `namespace="default"`.
3. This causes active shopping cart database connections across `cartservice` and `frontend` to drop immediately with timeout exceptions.
4. Output a clear confirmation brief: `"OUTAGE SIMULATION SUCCESSFUL: Active pods of GKE Deployment 'redis-cart' terminated. Database connection timeout condition triggered across cart services."`
