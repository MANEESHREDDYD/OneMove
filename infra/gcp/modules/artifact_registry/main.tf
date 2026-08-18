variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "asia-south1"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

resource "google_artifact_registry_repository" "docker_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "zonepilot-containers-${var.environment}"
  description   = "Immutable container images for ZonePilot (${var.environment})"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }
}

output "repository_id" {
  value = google_artifact_registry_repository.docker_repo.repository_id
}

output "repository_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}
