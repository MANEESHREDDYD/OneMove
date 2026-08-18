variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "database_url" {
  type        = string
  description = "PostgreSQL Database Connection URI"
  sensitive   = true
  default     = ""
}

variable "jwt_secret" {
  type        = string
  description = "JWT Signing Secret"
  sensitive   = true
  default     = ""
}

resource "google_secret_manager_secret" "db_url" {
  project   = var.project_id
  secret_id = "zonepilot-db-url-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_url_val" {
  count       = var.database_url != "" ? 1 : 0
  secret      = google_secret_manager_secret.db_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret" "jwt_sec" {
  project   = var.project_id
  secret_id = "zonepilot-jwt-secret-${var.environment}"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_sec_val" {
  count       = var.jwt_secret != "" ? 1 : 0
  secret      = google_secret_manager_secret.jwt_sec.id
  secret_data = var.jwt_secret
}

output "db_secret_id" {
  value = google_secret_manager_secret.db_url.secret_id
}

output "jwt_secret_id" {
  value = google_secret_manager_secret.jwt_sec.secret_id
}
