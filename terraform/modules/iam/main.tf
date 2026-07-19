# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

resource "google_service_account" "sre_agent_sa" {
  account_id   = "sre-agent-runner"
  display_name = "Autonomous SRE Agent Execution Service Account"
  project      = var.gcp_project_id
}

locals {
  roles = toset([
    "roles/aiplatform.user",
    "roles/container.developer",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/logging.viewer",
    "roles/monitoring.viewer",
    "roles/cloudtrace.agent",
    "roles/cloudtrace.viewer",
    "roles/errorreporting.viewer",
    "roles/mcp.toolUser",
    "roles/iap.egressor",
    "roles/storage.objectAdmin",
    "roles/cloudapiregistry.viewer",
    "roles/agentregistry.viewer",
    "roles/artifactregistry.writer",
    "roles/artifactregistry.admin"
  ])
}

resource "google_project_iam_member" "agent_roles" {
  for_each = local.roles
  project  = var.gcp_project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.sre_agent_sa.email}"
}

# Also ensure default compute service account has these permissions for Reasoning Engine backcompat
data "google_project" "project" {
  project_id = var.gcp_project_id
}

resource "google_project_iam_member" "default_compute_roles" {
  for_each = local.roles
  project  = var.gcp_project_id
  role     = each.key
  member   = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_sa_roles" {
  for_each = local.roles
  project  = var.gcp_project_id
  role     = each.key
  member   = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Override allowed policy member domains on project to allow public Cloud Run access (allUsers)
resource "google_project_organization_policy" "allow_all_domains" {
  project    = var.gcp_project_id
  constraint = "constraints/iam.allowedPolicyMemberDomains"

  list_policy {
    allow {
      all = true
    }
  }
}
