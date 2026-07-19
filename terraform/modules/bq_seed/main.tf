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

resource "google_bigquery_dataset" "sre_releases" {
  dataset_id                  = "sre_releases"
  friendly_name               = "Recent Release & Deployment Ledger"
  description                 = "Cross-signal deployment correlation database for NovaSRE autonomous triage."
  location                    = "US"
  delete_contents_on_destroy  = true
  project                     = var.gcp_project_id

  depends_on = [var.depends_on_apis]
}

resource "google_bigquery_table" "recent_releases" {
  dataset_id          = google_bigquery_dataset.sre_releases.dataset_id
  table_id            = "recent_releases"
  project             = var.gcp_project_id
  deletion_protection = false
  schema              = <<EOF
[
  {
    "name": "release_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique release identifier."
  },
  {
    "name": "service_name",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Target microservice name."
  },
  {
    "name": "namespace",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Kubernetes namespace."
  },
  {
    "name": "previous_revision",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Previous container image or stable release tag."
  },
  {
    "name": "new_revision",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "New container image or broken release tag."
  },
  {
    "name": "timestamp_utc",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Deployment execution timestamp."
  },
  {
    "name": "deployed_by",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "CI/CD system or user triggering the deployment."
  },
  {
    "name": "commit_hash",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Git commit hash."
  },
  {
    "name": "change_summary",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Summary of changes included in the rollout."
  }
]
EOF

  depends_on = [google_bigquery_dataset.sre_releases]
}

resource "terraform_data" "seed_bq_releases" {
  triggers_replace = [
    google_bigquery_table.recent_releases.id
  ]

  provisioner "local-exec" {
    command = <<-EOT
      export PATH=$PATH:/google/google-cloud-sdk/bin:/usr/lib/google-cloud-sdk/bin:/opt/google-cloud-sdk/bin:/usr/local/google-cloud-sdk/bin:/root/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin
      BQ_CMD=$(command -v bq || find / -name bq -type f 2>/dev/null | head -n 1)
      if [ -z "$BQ_CMD" ]; then echo "❌ bq CLI required to seed BigQuery table."; exit 1; fi

      echo "🌱 Seeding sre_releases.recent_releases with baseline deployment records..."
      $BQ_CMD --project_id=${var.gcp_project_id} query --use_legacy_sql=false \
      'INSERT INTO `${var.gcp_project_id}.sre_releases.recent_releases` (release_id, service_name, namespace, previous_revision, new_revision, timestamp_utc, deployed_by, commit_hash, change_summary) VALUES
      ("REL-20260718-042", "cartservice", "default", "gcr.io/google-samples/microservices-demo/cartservice:v1.0.4", "gcr.io/google-samples/microservices-demo/cartservice:broken-v2", CURRENT_TIMESTAMP(), "cloud-build-pipeline", "c83f91a2", "Updated shopping cart gRPC timeout and serialization format (Scenario 2 trigger)."),
      ("REL-20260718-038", "frontend", "default", "gcr.io/google-samples/microservices-demo/frontend:v0.9.8", "gcr.io/google-samples/microservices-demo/frontend:v1.0.0", TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR), "sre-automation", "a14f77c9", "Stable production UI update."),
      ("REL-20260718-035", "redis-cart", "default", "redis:6.2-alpine", "redis:7.0-alpine", TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY), "sre-automation", "e98a33b1", "Database engine minor release upgrade.")'

      echo "✅ BigQuery recent_releases table seeded successfully."
    EOT
  }

  depends_on = [google_bigquery_table.recent_releases]
}
