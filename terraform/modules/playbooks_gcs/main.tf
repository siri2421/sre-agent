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

resource "google_storage_bucket" "playbooks_bucket" {
  name                        = "${var.gcp_project_id}-sre-playbooks"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true
  project                     = var.gcp_project_id

  depends_on = [var.depends_on_apis]
}

resource "google_storage_bucket_object" "playbook_scale_recovery" {
  name   = "playbooks/gke-scale-recovery.md"
  bucket = google_storage_bucket.playbooks_bucket.name
  source = "${abspath(path.root)}/../app/skills/playbooks/gke-scale-recovery/SKILL.md"
}

resource "google_storage_bucket_object" "playbook_crashloop_rollback" {
  name   = "playbooks/gke-crashloop-rollback.md"
  bucket = google_storage_bucket.playbooks_bucket.name
  source = "${abspath(path.root)}/../app/skills/playbooks/gke-crashloop-rollback/SKILL.md"
}

resource "google_storage_bucket_object" "playbook_pod_restart" {
  name   = "playbooks/gke-pod-restart.md"
  bucket = google_storage_bucket.playbooks_bucket.name
  source = "${abspath(path.root)}/../app/skills/playbooks/gke-pod-restart/SKILL.md"
}

resource "google_storage_bucket_object" "playbook_horizontal_upsize" {
  name   = "playbooks/gke-horizontal-upsize.md"
  bucket = google_storage_bucket.playbooks_bucket.name
  source = "${abspath(path.root)}/../app/skills/playbooks/gke-horizontal-upsize/SKILL.md"
}
