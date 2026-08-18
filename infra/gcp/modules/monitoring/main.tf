variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

# 1. API 5xx Error Rate Alert
resource "google_monitoring_alert_policy" "api_5xx_errors" {
  project      = var.project_id
  display_name = "ZonePilot API High 5xx Errors (${var.environment})"
  combiner     = "OR"

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
  display_name = "ZonePilot Dead-Letter Messages (${var.environment})"
  combiner     = "OR"

  conditions {
    display_name = "Pub/Sub dead-letter topic received messages"
    condition_threshold {
      filter          = "resource.type = \"pubsub_topic\" AND metric.type = \"pubsub.googleapis.com/topic/send_request_count\""
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
