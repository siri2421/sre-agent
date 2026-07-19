---
name: gke-workloads
description: Diagnostic rules and OneMCP inspection patterns for generic Kubernetes workloads (Deployments, StatefulSets, Pods, Services, and Ingresses) on GKE. Call load_skill('gke-workloads') ONLY when your baseline telemetry or alert confirms that the affected resource is a GKE / Kubernetes workload that needs inspection.
---

# Universal GKE Workload Diagnostics

When investigating an alert involving Kubernetes resources (`Deployments`, `StatefulSets`, `Pods`, `DaemonSets`, `Services`) on GKE, use your generic **GKE OneMCP read-only tools** (`list_kubernetes_resources`, `get_pod_logs`) to verify the exact live state before and after any remediation.

## 1. Checking Replica Count & Scale Outages (`Active Replicas = 0`)
To check if a Deployment or StatefulSet has scaled to `0` or is failing to meet its target replica count:
* Call `list_kubernetes_resources(kind="Deployment", namespace="[NAMESPACE]")` (or `kind="StatefulSet"`).
* Inspect the returned JSON list `items[*].status` and `items[*].spec` fields for your target deployment:
  * Compare `status.readyReplicas` (or `status.availableReplicas`) against `spec.replicas`.
  * If `status.readyReplicas` is `0` or missing while `spec.replicas > 0` (or if `spec.replicas == 0`), confirm the replica scale anomaly.

## 2. Diagnosing Pod CrashLoops & Container Exit Codes
To check why a pod is crashing or failing to start:
* Call `list_kubernetes_resources(kind="Pod", namespace="[NAMESPACE]", label_selector="app=[APP_NAME]")`.
* Inspect `status.containerStatuses[*].state` and `status.containerStatuses[*].lastState`. Look for `CrashLoopBackOff`, `OOMKilled`, or non-zero exit codes (`exitCode: 137` = OOM, `exitCode: 1` = application crash).
* Call `get_pod_logs(name="[POD_NAME]", namespace="[NAMESPACE]", container="[CONTAINER_NAME]")` to retrieve the last 50 lines of container stderr/stdout.

## 3. Post-Remediation Health Verification
After calling `remediation_executor_remote` to execute a scale-up or rollback:
* You MUST query `list_kubernetes_resources` again to verify that `status.readyReplicas` matches `spec.replicas` and that new replacement pods have reached `Running` / `Ready: 1/1` state.
