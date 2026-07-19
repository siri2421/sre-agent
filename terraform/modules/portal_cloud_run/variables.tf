variable "gcp_project_id" {
  description = "Google Cloud Project ID."
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud region."
  type        = string
}

variable "investigator_agent_urn" {
  description = "Investigator Reasoning Engine URN."
  type        = string
  default     = ""
}

variable "remediation_agent_urn" {
  description = "Remediation Reasoning Engine URN."
  type        = string
  default     = ""
}

variable "outage_simulator_urn" {
  description = "Outage Simulator Reasoning Engine URN."
  type        = string
  default     = ""
}

variable "deploy_web_portal" {
  description = "Master toggle to deploy the UI to Cloud Run."
  type        = bool
}

variable "depends_on_agents" {
  description = "Dependency trigger on agent deployment."
  type        = string
}
