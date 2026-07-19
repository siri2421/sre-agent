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

resource "google_artifact_registry_repository" "portal_repo" {
  count         = var.deploy_web_portal ? 1 : 0
  location      = var.gcp_region
  repository_id = "novasre-repo"
  description   = "Docker repository for NovaSRE containers"
  format        = "DOCKER"
  project       = var.gcp_project_id
}

resource "terraform_data" "deploy_reasoning_engines" {
  count      = var.deploy_web_portal ? 1 : 0
  depends_on = [google_artifact_registry_repository.portal_repo]

  triggers_replace = [
    var.gcp_project_id,
    filemd5("${abspath(path.root)}/../app/remediation_agent.py"),
    filemd5("${abspath(path.root)}/../app/outage_simulator_agent.py"),
    filemd5("${abspath(path.root)}/../app/investigator_agent.py"),
    filemd5("${abspath(path.root)}/../deploy_a2a.py")
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      export PATH=$PATH:/google/google-cloud-sdk/bin:/usr/bin:/bin
      PYTHON_CMD=$(command -v python3 || find / -name python3 -type f 2>/dev/null | head -n 1)
      if [ -f "${abspath(path.root)}/../.venv/bin/python3" ]; then
        PYTHON_CMD="${abspath(path.root)}/../.venv/bin/python3"
      fi
      echo "🤖 Deploying 3x Vertex AI Reasoning Engine Agents via deploy_a2a.py..."
      cd ${abspath(path.root)}/.. && $PYTHON_CMD deploy_a2a.py
    EOT
  }
}

resource "terraform_data" "build_portal_image" {
  count = var.deploy_web_portal ? 1 : 0
  depends_on = [google_artifact_registry_repository.portal_repo, terraform_data.deploy_reasoning_engines]

  triggers_replace = [
    var.gcp_project_id,
    var.investigator_agent_urn,
    var.remediation_agent_urn,
    var.outage_simulator_urn,
    var.depends_on_agents,
    filemd5("${abspath(path.root)}/../ui/Dockerfile"),
    filemd5("${abspath(path.root)}/../ui/streamlit_app.py"),
    filemd5("${abspath(path.root)}/../ui/cloudbuild.yaml"),
    filemd5("${abspath(path.root)}/../ui/requirements.txt"),
    filemd5("${abspath(path.root)}/../app/requirements.txt"),
    filemd5("${abspath(path.root)}/../app/config.py")
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      export PATH=$PATH:/google/google-cloud-sdk/bin:/usr/lib/google-cloud-sdk/bin:/opt/google-cloud-sdk/bin:/usr/local/google-cloud-sdk/bin:/root/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin
      GCLOUD_CMD=$(command -v gcloud || find / -name gcloud -type f 2>/dev/null | head -n 1)
      if [ -z "$GCLOUD_CMD" ]; then echo "❌ gcloud CLI required to build container image."; exit 1; fi

      echo "📦 Building and pushing NovaSRE Control Room UI container from root repo context..."
      $GCLOUD_CMD builds submit ${abspath(path.root)}/.. \
        --project=${var.gcp_project_id} \
        --config=${abspath(path.root)}/../ui/cloudbuild.yaml \
        --substitutions=_IMAGE_URI=${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/novasre-repo/novasre-control-room:latest \
        --quiet
    EOT
  }
}

resource "google_cloud_run_v2_service" "portal" {
  count               = var.deploy_web_portal ? 1 : 0
  name                = "novasre-control-room"
  location            = var.gcp_region
  project             = var.gcp_project_id
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    annotations = {
      "terraform-build-trigger" = terraform_data.build_portal_image[0].id
    }

    containers {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/novasre-repo/novasre-control-room:latest"
      
      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gcp_region
      }
      env {
        name  = "INVESTIGATOR_AGENT_URN"
        value = var.investigator_agent_urn
      }
      env {
        name  = "REMEDIATION_AGENT_URN"
        value = var.remediation_agent_urn
      }
      env {
        name  = "OUTAGE_SIMULATOR_URN"
        value = var.outage_simulator_urn
      }
    }
  }

  depends_on = [terraform_data.build_portal_image]
}

resource "google_cloud_run_v2_service_iam_member" "invoker_access" {
  count    = var.deploy_web_portal ? 1 : 0
  project  = var.gcp_project_id
  location = var.gcp_region
  name     = google_cloud_run_v2_service.portal[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
