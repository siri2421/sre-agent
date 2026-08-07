---
name: gcp-error-reporting
description: Query Google Cloud Error Reporting pre-aggregated crash statistics, error groups, and deduplicated stack traces via the Error Reporting MCP tools (list_group_stats, get_group, list_events). Use this skill whenever the user asks about repeating application crashes, top exceptions, error rate spikes, stack traces, or recurring unhandled exceptions across GKE services, Cloud Run, or Compute Engine. Covers efficient grouping analysis, filtering by time windows and service names, and token-saving strategies by relying on pre-aggregated group statistics instead of scanning raw logs. DO NOT use for time-series charts (use gcp-monitoring) or tracing latency bottlenecks (use gcp-trace).
---

# GCP Error Reporting skill

You are querying **Cloud Error Reporting** through the Error Reporting MCP toolset. This skill teaches you how to efficiently analyze application crashes, inspect deduplicated stack traces, and correlate failures while enforcing strict token optimization to prevent context window bloating.

## Tools you have

| Tool | When to use |
|---|---|
| `list_group_stats` | **Primary triage tool.** Retrieve pre-aggregated statistics and counts for recurring error groups within a time window and target service. Very lightweight on tokens. |
| `get_group` | Check resolution state, tracking info, and metadata for a specific error group (`group_id`). |
| `list_events` | Pull representative error instances and complete stack traces for a specific group. **Use sparingly and page small** to prevent context bloat. |

## Hard rules (Token Optimization & Context Protection)

1. **Always start with pre-aggregated stats (`list_group_stats`).** Never immediately call `list_events` or search raw crash logs in Cloud Logging. `list_group_stats` returns compact, deduplicated error counts and impacted services at a fraction of the token cost.
2. **Restrict time windows & filter by service.** Always scope queries to explicit time intervals (e.g., `PERIOD_1_HOUR` or exact RFC3339 timestamps derived from `get_current_utc_time()`). Always supply `serviceFilter.service` when investigating a known GKE workload (e.g., `cartservice` or `paymentservice`).
3. **Limit representative crash events (`list_events`).** When retrieving exception stack traces for a specific `groupId`, restrict `pageSize` to 1 or 2 representative events. A single occurrence contains the complete exception stack trace; fetching dozens of identical crash events wastes tokens and severely inflates the context window.
4. **Synthesize stack traces.** When communicating findings or reasoning through root causes, report only the exception class, failing source filename, exact line number, and core error message. Do not dump lengthy multi-frame boilerplate stack traces (e.g., framework reflection loops) into your narrative output.
5. **Quote Project IDs correctly.** Always pass `projects/<PROJECT_ID>` or the parameter format explicitly demanded by the tool schema. Never invent project IDs.

## Standard investigation flow

1. **Triage dominant crash groups:** Call `list_group_stats` scoped to the active incident window (e.g., last 1 hour) and filtered by the target service name. Sort by error count to isolate the primary crash causing an outage or `CrashLoopBackOff`.
2. **Inspect representative exception:** Take the primary `groupId` from step 1 and execute `list_events` with `pageSize=1`. Extract the root exception class, error message, and failing source file/line number without excess token usage.
3. **Correlate with recent deployments:** Check the first seen timestamp (`firstSeenTime` or earliest occurrence) against recent releases using `sre-correlation` (e.g., querying BigQuery `sre_releases.recent_releases`). If a new crash group started immediately after a container image update, initiate rollback procedures (`gke-crashloop-rollback`).
4. **Pivot to trace or logs:** If the representative error event includes an associated `trackingId` or `trace_id`, transition to `gcp-trace` or `gcp-logging` to examine the accompanying request parameters and system logs.

## When NOT to use this skill

- For **non-exception operational logs** (e.g., access logs, info messages, audit trails) → use `gcp-logging`.
- For **metric time-series** (CPU utilization, OOM kill counters, request throughput) → use `gcp-monitoring`.
- For **per-request latency debugging** or span breakdowns → use `gcp-trace`.
