variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region for the subnetwork."
  type        = string
}

variable "deploy_infrastructure" {
  description = "Whether to create the VPC network and subnetwork."
  type        = bool
}

variable "depends_on_apis" {
  description = "API enablement dependency trigger."
  type        = string
}
