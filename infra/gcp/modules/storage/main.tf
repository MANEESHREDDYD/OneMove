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

variable "unique_suffix" {
  type        = string
  description = "Globally unique suffix for bucket naming"
}

resource "google_storage_bucket" "raw" {
  name                        = "zonepilot-${var.environment}-raw-${var.unique_suffix}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

resource "google_storage_bucket" "evidence" {
  name                        = "zonepilot-${var.environment}-evidence-${var.unique_suffix}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "artifacts" {
  name                        = "zonepilot-${var.environment}-artifacts-${var.unique_suffix}"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }
}

output "raw_bucket_name" {
  value = google_storage_bucket.raw.name
}

output "evidence_bucket_name" {
  value = google_storage_bucket.evidence.name
}

output "artifacts_bucket_name" {
  value = google_storage_bucket.artifacts.name
}
