variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region."
  type        = string
}

variable "staging_bucket_name" {
  description = "Staging bucket name for Agent Engine artifacts."
  type        = string
}

variable "service_account_email" {
  description = "Dedicated execution Service Account email."
  type        = string
}

variable "gemini_model" {
  description = "Gemini model name."
  type        = string
}

variable "deploy_agents" {
  description = "Master toggle to execute the Python deploy script."
  type        = bool
}

variable "depends_on_apis" {
  description = "API trigger."
  type        = string
}

variable "depends_on_iam" {
  description = "IAM trigger."
  type        = string
}
