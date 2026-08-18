variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "services" {
  type        = list(string)
  description = "List of GCP APIs to enable"
  default = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudbuild.googleapis.com",
    "iamcredentials.googleapis.com",
    "billingbudgets.googleapis.com",
    "compute.googleapis.com",
  ]
}

resource "google_project_service" "services" {
  for_each           = toset(var.services)
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

output "enabled_services" {
  value = [for s in google_project_service.services : s.service]
}
