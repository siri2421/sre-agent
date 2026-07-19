variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region."
  type        = string
}

variable "depends_on_apis" {
  description = "Trigger to wait for API enablement."
  type        = any
}
