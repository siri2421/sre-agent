output "portal_url" {
  description = "The live URL of the NovaSRE Control Room on Cloud Run."
  value       = var.deploy_web_portal ? google_cloud_run_v2_service.portal[0].uri : "skipped"
}
