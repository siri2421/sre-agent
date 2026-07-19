variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "depends_on_apis" {
  description = "API enablement dependency trigger."
  type        = string
}
