output "bq_dataset_id" {
  description = "The seeded BigQuery dataset ID."
  value       = google_bigquery_dataset.sre_releases.dataset_id
}

output "bq_table_id" {
  description = "The seeded BigQuery recent_releases table ID."
  value       = google_bigquery_table.recent_releases.table_id
}
