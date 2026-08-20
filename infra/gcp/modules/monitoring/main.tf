variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "notification_email" {
  type        = string
  description = "Email address for monitoring alert notifications"
  default     = ""
}

# Notification Channel
resource "google_monitoring_notification_channel" "email_channel" {
  count        = var.notification_email != "" ? 1 : 0
  project      = var.project_id
  display_name = "ZonePilot Alerts Email (${var.environment})"
  type         = "email"
  labels = {
    email_address = var.notification_email
  }
}

# 1. API 5xx Error Rate Alert
resource "google_monitoring_alert_policy" "api_5xx_errors" {
  project      = var.project_id
  display_name = "ZonePilot API High 5xx Errors (${var.environment})"
  combiner     = "OR"
  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email_channel[0].name] : []

  conditions {
    display_name = "Cloud Run 5xx response count"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
}

# 2. Dead-Letter Queue Alert
resource "google_monitoring_alert_policy" "dead_letter_alert" {
  project      = var.project_id
  display_name = "ZonePilot DLQ Backlog (${var.environment})"
  combiner     = "OR"
  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email_channel[0].name] : []

  conditions {
    display_name = "DLQ Backlog Size > 0"
    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"zonepilot-opt-dead-letter-sub-${var.environment}\" AND metric.type = \"pubsub.googleapis.com/subscription/num_unacked_messages_by_region\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  conditions {
    display_name = "Stuck DLQ Messages (Oldest Age)"
    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"zonepilot-opt-dead-letter-sub-${var.environment}\" AND metric.type = \"pubsub.googleapis.com/subscription/oldest_unacked_message_age_by_region\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 3600 # Alert if message is unacked in DLQ for > 1 hour
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
}

# 3. Worker Exhaustion Observation Alert
resource "google_monitoring_alert_policy" "worker_exhaustion_alert" {
  project      = var.project_id
  display_name = "ZonePilot Optimization Worker Exhaustion (${var.environment})"
  combiner     = "OR"
  # This can be informational, but we route it to the same channel
  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email_channel[0].name] : []

  conditions {
    display_name = "Worker Dead Letter Forwards"
    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"zonepilot-opt-worker-sub-${var.environment}\" AND metric.type = \"pubsub.googleapis.com/subscription/dead_letter_message_count\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
}

output "api_alert_policy_id" {
  value = google_monitoring_alert_policy.api_5xx_errors.id
}
