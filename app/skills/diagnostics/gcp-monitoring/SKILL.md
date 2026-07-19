---
name: gcp-monitoring
description: Query Google Cloud Monitoring metrics, alerts, and dashboards via the monitoring MCP tools (list_timeseries, query_range PromQL, list_metric_descriptors, list_alerts, list_alert_policies, list_dashboards). Use this skill whenever the user asks about CPU, memory, latency, error rate, request count, queue depth, GPU utilization, custom metrics, alert firing history, or any quantitative time-series question. Covers the Monitoring filter language, PromQL via Google Cloud Managed Service for Prometheus, aligners and reducers, distribution metrics with exemplar trace IDs, and how to discover the right metric.type for a service. DO NOT use for log searches (use gcp-logging) or trace span timing (use gcp-trace).
---

# GCP Monitoring skill

You are querying **Cloud Monitoring** through the monitoring MCP toolset. This skill teaches you how to pick the right metric, write a correct filter, aggregate the data sensibly, and pivot from a metric value to a concrete trace or log entry.

## Tools

| Tool | When to use |
|---|---|
| `list_metric_descriptors` | Discover metric types. **Only with a `filter` argument** (see Hard rules below). |
| `list_timeseries` | **Primary numeric tool.** Pull data points for a specific `metric.type` over a time interval, optionally aggregated. |
| `query_range` | PromQL queries via Managed Prometheus — best for ratios, rates, histogram quantiles, multi-metric math. |
| `list_alert_policies` / `get_alert_policy` | What alerts are configured? |
| `list_alerts` / `get_alert` | What alerts have actually fired? Always check this first when investigating an incident. |
| `list_dashboards` / `get_dashboard` | Find existing dashboards that already chart the relevant signals. |

## Hard rules

1. **NEVER call `list_metric_descriptors` without a `filter`.** The unfiltered response routinely exceeds payload limits. Always narrow by service prefix:
   ```
   filter: metric.type = starts_with("run.googleapis.com/")
   filter: metric.type = starts_with("kubernetes.io/")
   filter: metric.type = starts_with("compute.googleapis.com/")
   filter: metric.type = starts_with("aiplatform.googleapis.com/")
   filter: metric.type = starts_with("loadbalancing.googleapis.com/")
   filter: metric.type = starts_with("cloudsql.googleapis.com/")
   ```
2. **`list_timeseries` requires:** `name = "projects/<PROJECT>"`, `filter` (single metric type), `interval` (`{startTime, endTime}`), and `view` (`FULL` or `HEADERS`). Use `HEADERS` first to confirm series exist before pulling points.
3. **Always pick a sensible `aggregation`.** Raw points across many resources is wasteful. See `references/aggregation.md`.
4. **Time intervals are RFC3339.** `2026-04-21T18:00:00Z`. Default window: **last 1 hour** for live investigations, **last 6 hours** for trend questions.
5. **Use the configured project ID.** Never invent project IDs.

## Standard investigation flow

1. **Check alerts first.** `list_alerts` filtered to the time window. Alerts often pre-package the root cause hypothesis.
2. **Find the right metric.** If you don't know it, run `list_metric_descriptors` with a service-prefix filter, then pick the smallest set of `metric.type`s that answers the question.
3. **Pull the data.** Prefer **PromQL via `query_range`** for: rates, ratios (e.g. error rate = 5xx / all), histogram quantiles (`histogram_quantile`), and any math across two metrics. Prefer **`list_timeseries`** for raw inspection of a single metric or when you need explicit aligner/reducer control.
4. **Aggregate.** Default: `alignmentPeriod = "60s"`, `perSeriesAligner = "ALIGN_RATE"` for counters and `ALIGN_MEAN` for gauges, `crossSeriesReducer = "REDUCE_SUM"` (counters) or `REDUCE_MEAN` (gauges), grouped by the most diagnostic label (often `resource.label."service_name"` or `metric.label."response_code_class"`).
5. **Pivot to logs/traces.** If you find a spike, hand off to `sre-correlation`:
   - For **distribution / histogram metrics**, look at the **exemplar trace IDs** attached to buckets — these point straight at a slow request.
   - For non-distribution metrics, use the metric's `monitored_resource` labels to build a Cloud Logging filter (same `resource.type` + same labels).

## When NOT to use this skill

- Listing/searching log lines → `gcp-logging`.
- Per-request span breakdown → `gcp-trace`.
- Recurring crash group counts → `gcp-error-reporting`.
