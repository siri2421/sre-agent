output "cluster_name" {
  description = "The GKE cluster name."
  value       = var.deploy_infrastructure ? google_container_cluster.online_boutique[0].name : "skipped"
}

output "cluster_endpoint" {
  description = "The GKE cluster endpoint IP."
  value       = var.deploy_infrastructure ? google_container_cluster.online_boutique[0].endpoint : "skipped"
}

output "cluster_id" {
  description = "The GKE cluster resource ID."
  value       = var.deploy_infrastructure ? google_container_cluster.online_boutique[0].id : "skipped"
}
