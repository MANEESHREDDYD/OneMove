variable "project_id" {
  type        = string
  description = "Production GCP Project ID"
  default     = "zonepilot-prod-9a4285"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "asia-south1"
}

variable "billing_account" {
  type        = string
  description = "GCP Billing Account ID"
  default     = "01BA6E-C859BE-27A85F"
}

variable "unique_suffix" {
  type        = string
  description = "Unique resource suffix"
  default     = "9a4285"
}

variable "api_image" {
  type        = string
  description = "ZonePilot API container image"
  default     = "gcr.io/cloudrun/hello"
}

variable "worker_image" {
  type        = string
  description = "ZonePilot Worker container image"
  default     = "gcr.io/cloudrun/hello"
}
