---
name: postmortem-aggregator
description: Aggregates and crunches metrics across multiple incident PostMortem files to maintain statistics, outage duration graphs, and trend analysis tables in POMO_AGGREGATED.md.
metadata:
  author: SRE Platform Team
  version: 1.0.0
  status: published
---

# 🐉 SRE PostMortem Aggregator Skill

You are an SRE metrics compiler. Use this skill when processing multiple PostMortem reports to aggregate incident metrics, calculate Mean Time to Detect (MTTD) and Mean Time to Recover (MTTR), and generate summary tables.

## Action Steps

1. **Identify PostMortem Reports**:
   - Inspect local or GCS postmortem Markdown files (`post_mortem_*.md`).
2. **Extract Key Metrics**:
   - Outage start timestamp (`incident_start_time`).
   - Incident detection timestamp (`detection_time`).
   - First mitigation timestamp (`mitigation_timestamp`).
   - Incident resolution timestamp (`resolution_time`).
   - Affected product area / microservice.
3. **Compile Aggregate Summary**:
   - Generate summary statistics for total outage minutes, microservice reliability trends, and recurring failure modes.
   - Maintain/update `POMO_AGGREGATED.md`.
