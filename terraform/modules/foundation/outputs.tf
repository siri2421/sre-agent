output "apis_enabled" {
  description = "Dependency trigger indicating required GCP APIs are fully enabled."
  value       = google_project_service.required_apis["aiplatform.googleapis.com"].id
}

output "staging_bucket_name" {
  description = "Name of the GCS bucket created for staging and telemetry."
  value       = google_storage_bucket.telemetry_bucket.name
}

output "staging_bucket_url" {
  description = "gs:// URL of the staging bucket."
  value       = "gs://${google_storage_bucket.telemetry_bucket.name}"
}
