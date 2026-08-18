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

variable "tier" {
  type        = string
  description = "Machine tier for Cloud SQL"
  default     = "db-custom-1-3840"
}

variable "db_password" {
  type        = string
  description = "Database master user password"
  sensitive   = true
}

resource "google_sql_database_instance" "postgres" {
  project             = var.project_id
  name                = "zonepilot-pg-${var.environment}"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = var.environment == "production" ? true : false

  settings {
    tier              = var.tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = 20
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 14
      }
    }

    ip_configuration {
      ipv4_enabled = true
      # Restrict public networks, Cloud Run connects via Cloud SQL Auth Proxy / Connector
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }

    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }
  }
}

resource "google_sql_database" "database" {
  project  = var.project_id
  name     = "zonepilot"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  project  = var.project_id
  name     = "zonepilot_app"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

output "instance_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "public_ip_address" {
  value = google_sql_database_instance.postgres.public_ip_address
}

output "database_name" {
  value = google_sql_database.database.name
}

output "db_user" {
  value = google_sql_user.app_user.name
}
