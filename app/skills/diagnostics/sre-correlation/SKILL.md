---
name: sre-correlation
description: Cross-signal correlation playbooks for Google Cloud observability — how to walk between traces, logs, metrics, and error groups using the IDs and labels that link them. Use this skill whenever an investigation has produced one piece of evidence (a slow trace, a noisy log, a metric spike, an error group) and you need to find the matching evidence in another signal. Covers four core pivots — trace_id ↔ logs (via the `trace` field), MonitoredResource ↔ logs (via shared resource labels), AppHub labels (`apphub.googleapis.com/application|service|workload`) for cross-service slicing, and exemplar trace IDs in distribution histograms (latency p99 → specific slow request).
---

# SRE correlation skill

A single signal almost never tells the full story. This skill is the glue: it teaches the four practical pivots that connect Cloud Trace, Cloud Logging, Cloud Monitoring, and Cloud Error Reporting via the IDs and labels they share. Use the per-API skills (`gcp-logging`, `gcp-monitoring`, `gcp-trace`, `gcp-error-reporting`) to actually run the calls; this skill says **which call to run next and what to fill in**.

## The four pivots

| From | To | Mechanism |
|---|---|---|
| Trace ID (or span ID) | All logs for that request | Cloud Logging `trace = "projects/<PID>/traces/<TID>"` |
| Metric series | The logs for the same resource | Reuse `resource.type` + `resource.labels.*` from the metric in a Logging filter |
| Any signal | Cross-service / app-level slicing | `apphub.googleapis.com/application` + `/service` + `/workload` labels |
| Latency p99 spike (distribution metric) | The exact slow request | Exemplars on distribution points → trace ID |
| Pod CrashLoop / 5xx burst | Correlated code/image deployment | BigQuery SQL query on `sre_releases.recent_releases` |

## When to use this skill

- "We see latency spiking — find me the slow request and its logs."
- "Error Reporting shows a new group — what's the actual stack and which request triggered it?"
- "There's a 5xx burst on service X — find traces and logs that explain it."
- "Cartservice pod entered CrashLoopBackOff — check what release was just deployed and correlate the failure."
- Anything where you have **one** piece of evidence and need to triangulate across signals or deployment ledgers.

## Hard rules

1. **Carry the time window.** Whatever signal you started in, propagate the same `[start, end]` to the next signal (widen by 1–2 minutes on each side to allow for clock skew).
2. **Carry the resource labels.** If you found the issue on GKE workload `checkout`, the next call must scope to the same namespace and workload name. Don't drop labels — that's how you end up with unrelated noise.
3. **Always quote the project ID** the same way the API expects it (bare ID for Trace; `projects/<PID>` for Logging/Monitoring; `projects/<PID>/traces/<TID>` for the Logging `trace` field).
4. **One pivot at a time.** Don't combine two pivots in one mental hop — write down the intermediate IDs/labels.

## Standard correlation playbook (the canonical SRE walk)

When investigating an outage, walk the signals in this order:

1. **Start in `gcp-monitoring.list_alerts`** — has anything fired? Open alerts have pre-built context (which condition, which resource).
2. **Check the BigQuery Recent Release Database (Deployment Correlation)**:
   - If the resource is in `CrashLoopBackOff` or experiencing sudden errors after a rollout, execute a SQL query via BigQuery OneMCP (`execute_sql`):
     `SELECT * FROM sre_releases.recent_releases WHERE service_name = '<target_service>' ORDER BY timestamp_utc DESC LIMIT 1;`
   - If the timestamp correlates (`delta < 15m`), report the correlated release ID (`REL-...`) and trigger **Playbook 2 (Tier 1 Auto-Rollback)** to revert to `previous_revision`.
3. **Confirm the spike numerically** in `gcp-monitoring.list_timeseries` (or PromQL).
4. **If the spiking metric is a distribution**, harvest **exemplar trace IDs**.
   - Otherwise, copy the metric's `resource.type` + `resource.labels` and call `gcp-logging.list_log_entries` with a matching scope and `severity >= ERROR`.
5. **Pick a target trace ID** (from exemplar, or from a log entry's `trace` field). Run `gcp-trace.get_trace`.
6. **Identify the bottleneck span.** Its service/operation tells you where to keep digging.
7. **Pull all logs for that trace** with `gcp-logging.list_log_entries` filtered by `trace = "projects/<PID>/traces/<TID>"`.
8. **If recurring**, check `gcp-error-reporting.list_group_stats` filtered to the same service in the same time window.
9. **If multi-service**, slice everything by AppHub labels to keep the lens on the affected application boundary.
