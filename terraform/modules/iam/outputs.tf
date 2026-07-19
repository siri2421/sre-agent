output "sre_agent_sa_email" {
  description = "The email of the dedicated SRE Agent Service Account."
  value       = google_service_account.sre_agent_sa.email
}

output "sre_agent_sa_name" {
  description = "The fully qualified resource name of the SRE Agent Service Account."
  value       = google_service_account.sre_agent_sa.name
}
