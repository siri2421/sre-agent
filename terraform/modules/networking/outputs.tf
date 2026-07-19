output "network_name" {
  description = "The name of the created VPC network."
  value       = var.deploy_infrastructure ? google_compute_network.vpc[0].name : "skipped"
}

output "network_id" {
  description = "The ID of the created VPC network."
  value       = var.deploy_infrastructure ? google_compute_network.vpc[0].id : "skipped"
}

output "subnetwork_name" {
  description = "The name of the created subnetwork."
  value       = var.deploy_infrastructure ? google_compute_subnetwork.subnet[0].name : "skipped"
}

output "subnetwork_id" {
  description = "The ID of the created subnetwork."
  value       = var.deploy_infrastructure ? google_compute_subnetwork.subnet[0].id : "skipped"
}
