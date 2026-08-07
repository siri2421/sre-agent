---
name: gcp-trace
description: Query Google Cloud Trace latency data and request span breakdowns via the trace MCP tools (list_traces, get_trace). Use this skill whenever the user asks about slow requests, latency p99 bottlenecks, span timing breakdown, or to locate high-latency requests using trace IDs harvested from monitoring distribution exemplars or logging trace fields. Covers time-window restrictions, filtering by latency thresholds, small pagination, and how to interpret span hierarchical structures without causing context bloat. DO NOT use for general metrics (use gcp-monitoring) or raw log searches (use gcp-logging).
---

# GCP Trace skill

You are querying **Cloud Trace** through the trace MCP toolset. This skill teaches you how to investigate latency bottlenecks, inspect span timing hierarchies, and extract diagnostic context while enforcing strict token optimization to prevent context window bloating.

## Tools you have

| Tool | When to use |
|---|---|
| `list_traces` | Discover and filter traces across a time window. **Always apply time filters and latency minimums** to avoid scanning large datasets. |
| `get_trace` | **Primary deep-dive tool.** Retrieve full span hierarchy for a single specific `trace_id` obtained from logs or metrics exemplars. Use ONLY for targeted investigations. |

## Hard rules (Token Optimization & Context Protection)

1. **Never execute unbounded trace lists.** Always scope queries with explicit time windows (`startTime`, `endTime` via RFC3339 timestamps derived from `get_current_utc_time()`, e.g., last 15–30 minutes). Unbounded queries return massive JSON payloads that exhaust token limits.
2. **Filter by latency minimums.** When searching for performance bottlenecks with `list_traces`, restrict queries using latency thresholds (e.g., `>= 1000ms` or `>= 2s`) to eliminate benign background traffic from the context window.
3. **Page small.** Set `pageSize` between 5 and 15 maximum for exploratory lookups. Full span hierarchies contain numerous child spans; large page sizes cause severe context bloat.
4. **Targeted deep-dive over broad scans.** Always prefer pivoting from an exemplar trace ID in Cloud Monitoring or a `trace` field in Cloud Logging directly to `get_trace` rather than listing traces broadly.
5. **Synthesize and prune span hierarchies.** When reasoning about or communicating results, report only the critical path spans—specifically the slowest span (highest self-time) or errored spans (HTTP 5xx / gRPC errors). Never dump complete raw JSON span arrays into chat or agent responses.
6. **Quote Project IDs correctly.** Always supply bare project IDs for Trace tools unless explicit path formatting (`projects/<PID>/traces/<TID>`) is specified by the schema.

## Standard investigation flow

1. **Receive trace ID or establish window:** Obtain a concrete `trace_id` from a Cloud Monitoring histogram exemplar or an ERROR log entry in Cloud Logging. If no ID is provided, check `get_current_utc_time()` and run `list_traces` bounded to the last 15 minutes with a strict latency threshold (`>= 1000ms`) and `pageSize=5`.
2. **Retrieve targeted trace hierarchy:** Call `get_trace(project_id, trace_id)`.
3. **Isolate critical bottlenecks:** Examine the span tree:
   - Identify spans with high self-time (total time minus child span times).
   - Look for spans with non-zero error codes or timeout annotations (`DEADLINE_EXCEEDED`, `504 Gateway Timeout`).
   - Identify the specific underlying microservice or gRPC dependency causing the latency spike.
4. **Pivot to logs:** Take the target `trace_id` and hand off to `gcp-logging` using filter `trace = "projects/<PROJECT_ID>/traces/<TRACE_ID>"` to view exact log entries emitted during that exact request execution.

## When NOT to use this skill

- For **aggregate latency trends** over time (p50/p95/p99 graphs or service Service Level Objectives) → use `gcp-monitoring`.
- For **searching text logs** or error payloads → use `gcp-logging`.
- For **recurring application crashes** or deduplicated exception statistics → use `gcp-error-reporting`.
