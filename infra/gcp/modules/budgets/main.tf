variable "billing_account" {
  type        = string
  description = "Billing Account ID"
}

variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "budget_amount" {
  type        = number
  description = "Monthly budget amount in USD"
  default     = 50
}

resource "google_billing_budget" "budget" {
  billing_account = var.billing_account
  display_name    = "ZonePilot Budget (${var.environment})"

  budget_filter {
    projects = ["projects/${var.project_id}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.75
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 0.9
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }
}

output "budget_id" {
  value = google_billing_budget.budget.id
}
