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

resource "google_container_cluster" "online_boutique" {
  count = var.deploy_infrastructure ? 1 : 0

  name     = "online-boutique"
  location = var.gcp_region
  project  = var.gcp_project_id

  network    = var.network_name
  subnetwork = var.subnetwork_name

  enable_autopilot = true

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods-range"
    services_secondary_range_name = "gke-services-range"
  }

  deletion_protection = false
}

resource "terraform_data" "deploy_microservices_demo" {
  count = var.deploy_infrastructure ? 1 : 0

  triggers_replace = [
    google_container_cluster.online_boutique[0].id,
    google_container_cluster.online_boutique[0].endpoint
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      export PATH=$PATH:/google/google-cloud-sdk/bin:/usr/lib/google-cloud-sdk/bin:/opt/google-cloud-sdk/bin:/usr/local/google-cloud-sdk/bin:/root/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin
      GCLOUD_CMD=$(command -v gcloud || find / -name gcloud -type f 2>/dev/null | head -n 1)
      KUBECTL_CMD=$(command -v kubectl || find / -name kubectl -type f 2>/dev/null | head -n 1)
      
      if [ -z "$GCLOUD_CMD" ]; then echo "❌ gcloud CLI required to authenticate GKE cluster."; exit 1; fi
      if [ -z "$KUBECTL_CMD" ]; then echo "❌ kubectl CLI required to apply manifests."; exit 1; fi

      echo "Connecting to GKE Autopilot cluster ${google_container_cluster.online_boutique[0].name}..."
      $GCLOUD_CMD container clusters get-credentials ${google_container_cluster.online_boutique[0].name} --region=${var.gcp_region} --project=${var.gcp_project_id} --quiet

      echo "Deploying Online Boutique microservices-demo application from GitHub..."
      $KUBECTL_CMD apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/microservices-demo/main/release/kubernetes-manifests.yaml

      echo "✅ Online Boutique application deployed successfully."
    EOT
  }

  depends_on = [google_container_cluster.online_boutique]
}
