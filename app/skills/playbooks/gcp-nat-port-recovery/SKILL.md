---
name: gcp-nat-port-recovery
description: Playbook 7 (Tier 2 HITL Approval) — Use when Cloud NAT egress gateway experiences SNAT port exhaustion or dropped packets on outbound connections from GKE workloads.
---

# SRE Playbook 7: Cloud NAT Egress Port Exhaustion & Packet Drop Recovery

## Target Scenario
* **Target Component**: Cloud NAT Router (`nat-gateway-us-central1`).
* **Diagnostic Trigger**: `rca_telemetry_expert` isolates SNAT port allocation exhaustion (`allocated_ports` metric cap reached) or `dropped_sent_packets_count > 0` on Cloud NAT router.

## Remediation Action (Tier 2 - HITL Approval Required)
1. Present the recommended Cloud NAT scaling plan to the human operator: `"Increase minimum allocated ports per VM from 64 to 256 on Cloud NAT gateway 'nat-gateway-us-central1' in region us-central1."`
2. Upon operator approval (`APPROVED`), call `remediation_executor_remote("gcloud compute routers nats update nat-gateway-us-central1 --router=nat-router-us-central1 --min-ports-per-vm=256 --region=us-central1")`.
3. Verify that dropped packet count returns to `0` and report `SUCCESS`.
