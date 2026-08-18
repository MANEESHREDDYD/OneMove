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

variable "api_image" {
  type        = string
  description = "Container image URL for ZonePilot API"
}

variable "worker_image" {
  type        = string
  description = "Container image URL for Optimizer Worker"
}

variable "api_sa_email" {
  type        = string
  description = "Service account email for API"
}

variable "worker_sa_email" {
  type        = string
  description = "Service account email for Worker"
}

variable "db_instance_connection_name" {
  type        = string
  description = "Cloud SQL instance connection name"
  default     = ""
}

# 1. ZonePilot API Cloud Run Service
resource "google_cloud_run_v2_service" "api" {
  name     = "zonepilot-api-${var.environment}"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = var.api_sa_email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = var.api_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1024Mi"
        }
      }

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }
}

# Allow unauthenticated public access to API (auth handled by JWT middleware)
resource "google_cloud_run_service_iam_member" "api_public" {
  location = google_cloud_run_v2_service.api.location
  project  = var.project_id
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 2. ZonePilot Optimizer Worker Service
resource "google_cloud_run_v2_service" "worker" {
  name     = "zonepilot-worker-${var.environment}"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = var.worker_sa_email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = var.worker_image

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2048Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }
}

output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "worker_url" {
  value = google_cloud_run_v2_service.worker.uri
}
