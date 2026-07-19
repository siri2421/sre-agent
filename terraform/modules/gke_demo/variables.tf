variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region for the cluster."
  type        = string
}

variable "network_name" {
  description = "VPC network name."
  type        = string
}

variable "subnetwork_name" {
  description = "Subnetwork name."
  type        = string
}

variable "deploy_infrastructure" {
  description = "Whether to provision the GKE cluster and demo application."
  type        = bool
}

variable "depends_on_apis" {
  description = "API enablement dependency trigger."
  type        = string
}
