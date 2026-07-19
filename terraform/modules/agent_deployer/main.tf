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

resource "terraform_data" "run_python_deployer" {
  count = var.deploy_agents ? 1 : 0

  triggers_replace = [
    var.gcp_project_id,
    var.gemini_model,
    var.service_account_email
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      export PATH=$PATH:/google/google-cloud-sdk/bin:/usr/lib/google-cloud-sdk/bin:/opt/google-cloud-sdk/bin:/usr/local/google-cloud-sdk/bin:/root/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin
      export GCP_PROJECT_ID=${var.gcp_project_id}
      export GOOGLE_CLOUD_LOCATION=${var.gcp_region}
      export STAGING_BUCKET=gs://${var.staging_bucket_name}
      export REASONING_ENGINE_SERVICE_ACCOUNT=${var.service_account_email}
      export GEMINI_MODEL=${var.gemini_model}

      echo "🚀 Launching automated build & deployment to Vertex AI Reasoning Engine..."
      echo "Target Project: $GCP_PROJECT_ID | Region: $GOOGLE_CLOUD_LOCATION | SA: $REASONING_ENGINE_SERVICE_ACCOUNT"

      PYTHON_CMD=$(command -v python3 || find / -name python3 -type f 2>/dev/null | head -n 1)
      if [ -f "${abspath(path.root)}/../.venv/bin/python3" ]; then
        PYTHON_CMD="${abspath(path.root)}/../.venv/bin/python3"
      fi

      cd ${abspath(path.root)}/.. && $PYTHON_CMD deploy_a2a.py

      echo "✅ SRE Reasoning Engine deployment step finished."
    EOT
  }
}
