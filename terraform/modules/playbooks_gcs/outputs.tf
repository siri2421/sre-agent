output "playbooks_bucket_name" {
  description = "The GCS bucket where modular SRE playbooks are stored and synced."
  value       = google_storage_bucket.playbooks_bucket.name
}
