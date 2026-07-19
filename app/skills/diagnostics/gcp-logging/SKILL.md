---
name: gcp-logging
description: Query Google Cloud Logging effectively via the logging MCP tools (list_log_entries, list_log_names, list_buckets, list_views). Use this skill whenever the user asks about logs, log entries, error messages in logs, audit logs, or you need raw log evidence to back up a finding. Covers the Logging Query Language (LRL), indexed fields for fast queries, severity filters, time-window restrictions, structured payload (jsonPayload) traversal, and how to scope queries to a specific resource (Cloud Run service, GKE workload, GCE instance, etc.). DO NOT use this skill for aggregated error stats — use gcp-error-reporting for that.
---

# GCP Logging skill

You are querying **Cloud Logging** through the logging MCP toolset. This skill teaches you how to write **selective, fast, low-payload** filters and how to interpret `LogEntry` results.

## Tools you have

| Tool | When to use |
|---|---|
| `list_log_entries` | **Primary.** Search/retrieve log entries with a filter. Always supply `resourceNames` and `filter`. |
| `list_log_names` | Discover what logs (e.g. `cloudaudit.googleapis.com/activity`) exist in a project. Cheap. |
| `list_buckets` / `get_bucket` | Inspect log storage configuration (rare; only when troubleshooting retention/routing). |
| `list_views` / `get_view` | Inspect log views (rare; only for access-control questions). |

## Hard rules

1. **`resourceNames` is required.** Always pass `["projects/<PROJECT_ID>"]` (use the configured project ID; never invent one). Multiple projects in one call **will fail**.
2. **Always include a `timestamp` restriction** in the filter. Without one you scan everything and the response is huge. Default to the last 1 hour for active investigations, last 15 minutes when correlating with a known incident time.
3. **Always include a `resource.type` restriction** unless the user explicitly wants project-wide. This is the single biggest payload-size lever.
4. **Use indexed fields first** (`resource.type`, `resource.labels.*`, `severity`, `logName`, `timestamp`, `trace`, `httpRequest.status`, `labels.*`). Free-text search via `:` is slow and last-resort.
5. **Page small.** Set `pageSize` to 20–50 for first probe, then increase only if needed.
6. **Order:** Use `orderBy="timestamp desc"` to get the most recent issues first when investigating an active outage.

## Standard investigation flow

1. **Establish scope.** Confirm the resource type and project. If the user is vague, prefer `resource.type=("cloud_run_revision" OR "k8s_container" OR "gce_instance")` over no filter.
2. **Bound time tightly.** `timestamp >= "2026-04-21T18:00:00Z" AND timestamp < "2026-04-21T18:30:00Z"`.
3. **Filter by severity** for triage: `severity >= ERROR`.
4. **Pivot.** If you find a `trace` field on a hit, hand off to `sre-correlation` (trace-to-logs reference) to pull every log on that request.
5. **Dig into payloads.** For structured logs use `jsonPayload.field = "value"`. For unstructured, `textPayload:"substring"`.

## When NOT to use this skill

- For **counts/trends/group statistics** of recurring crashes → use `gcp-error-reporting`.
- For **metric values** (CPU, memory, latency p99) → use `gcp-monitoring`.
- For **per-request span timings** → use `gcp-trace`.
