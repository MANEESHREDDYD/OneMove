variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
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

# Worker Subscription with Dead-Letter Policy
resource "google_pubsub_subscription" "worker_sub" {
  project              = var.project_id
  name                 = "zonepilot-opt-worker-sub-${var.environment}"
  topic                = google_pubsub_topic.optimization_jobs.name
  ack_deadline_seconds = 300

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
