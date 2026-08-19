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

variable "release_sha" {
  type        = string
  description = "Source code Git commit SHA for immutable release identity"
  default     = ""
}

variable "api_image" {
  type        = string
  description = "Container image URL for ZonePilot API"
}

variable "worker_image" {
  type        = string
  description = "Container image URL for Optimizer Worker"
}

variable "dispatcher_image" {
  type        = string
  description = "Container image URL for Outbox Dispatcher"
  default     = ""
}

variable "api_sa_email" {
  type        = string
  description = "Service account email for API"
}

variable "worker_sa_email" {
  type        = string
  description = "Service account email for Worker"
}

variable "dispatcher_sa_email" {
  type        = string
  description = "Service account email for Outbox Dispatcher"
  default     = ""
}

variable "pubsub_push_sa_email" {
  type        = string
  description = "Service account email for Pub/Sub push invoker"
  default     = ""
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

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "ZONEPILOT_APP_VERSION"
        value = "1.5.1"
      }

      env {
        name  = "ZONEPILOT_GIT_SHA"
        value = var.release_sha
      }

      env {
        name  = "ZONEPILOT_SCHEMA_VERSION"
        value = "1.0.0"
      }

      env {
        name  = "PUBSUB_TOPIC_OPTIMIZATIONS"
        value = "zonepilot-opt-jobs-${var.environment}"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "zonepilot-db-url-${var.environment}"
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "zonepilot-jwt-secret-${var.environment}"
            version = "latest"
          }
        }
      }
    }
  }
}

# Allow unauthenticated public access to API (auth handled by JWT middleware)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  location = google_cloud_run_v2_service.api.location
  project  = var.project_id
  name     = google_cloud_run_v2_service.api.name
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

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "ZONEPILOT_GIT_SHA"
        value = var.release_sha
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "zonepilot-db-url-${var.environment}"
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "zonepilot-jwt-secret-${var.environment}"
            version = "latest"
          }
        }
      }
    }
  }
}

# Grant Pub/Sub OIDC Service Account Invoker permissions on Worker
resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  location = google_cloud_run_v2_service.worker.location
  project  = var.project_id
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.pubsub_push_sa_email != "" ? var.pubsub_push_sa_email : var.worker_sa_email}"
}

# 3. ZonePilot Outbox Dispatcher Service (Continuous background daemon)
resource "google_cloud_run_v2_service" "dispatcher" {
  name     = "zonepilot-dispatcher-${var.environment}"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = var.dispatcher_sa_email != "" ? var.dispatcher_sa_email : var.api_sa_email

    scaling {
      min_instance_count = 1
      max_instance_count = 2
    }

    containers {
      image = var.dispatcher_image != "" ? var.dispatcher_image : var.worker_image

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

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "PUBSUB_TOPIC_OPTIMIZATIONS"
        value = "zonepilot-opt-jobs-${var.environment}"
      }

      env {
        name  = "ZONEPILOT_GIT_SHA"
        value = var.release_sha
      }

      env {
        name  = "DISPATCHER_INTERVAL_SEC"
        value = "2"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "zonepilot-db-url-${var.environment}"
            version = "latest"
          }
        }
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

output "dispatcher_url" {
  value = google_cloud_run_v2_service.dispatcher.uri
}
