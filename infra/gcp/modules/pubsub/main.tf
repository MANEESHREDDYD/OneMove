variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "push_endpoint" {
  type        = string
  description = "Worker Cloud Run push endpoint URL"
  default     = ""
}

variable "push_service_account_email" {
  type        = string
  description = "Service account email for Pub/Sub OIDC push authorization"
  default     = ""
}

# Dead Letter Topic
resource "google_pubsub_topic" "dead_letter" {
  project = var.project_id
  name    = "zonepilot-opt-dead-letter-${var.environment}"
}

# Primary Optimization Jobs Topic
resource "google_pubsub_topic" "optimization_jobs" {
  project = var.project_id
  name    = "zonepilot-opt-jobs-${var.environment}"
}

# Worker Subscription with Dead-Letter Policy and Authenticated Push Config
resource "google_pubsub_subscription" "worker_sub" {
  project              = var.project_id
  name                 = "zonepilot-opt-worker-sub-${var.environment}"
  topic                = google_pubsub_topic.optimization_jobs.name
  ack_deadline_seconds = 300

  dynamic "push_config" {
    for_each = var.push_endpoint != "" ? [1] : []
    content {
      push_endpoint = var.push_endpoint

      dynamic "oidc_token" {
        for_each = var.push_service_account_email != "" ? [1] : []
        content {
          service_account_email = var.push_service_account_email
          audience              = var.push_endpoint
        }
      }
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

output "topic_name" {
  value = google_pubsub_topic.optimization_jobs.name
}

output "topic_id" {
  value = google_pubsub_topic.optimization_jobs.id
}

output "subscription_name" {
  value = google_pubsub_subscription.worker_sub.name
}

output "subscription_id" {
  value = google_pubsub_subscription.worker_sub.id
}

output "dead_letter_topic_name" {
  value = google_pubsub_topic.dead_letter.name
}
