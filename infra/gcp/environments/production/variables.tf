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
  description = "Container image URL for OneMove API"
  default     = "asia-south1-docker.pkg.dev/zonepilot-prod-9a4285/zonepilot-containers-production/zonepilot-api:latest"
}

variable "worker_image" {
  type        = string
  description = "Container image URL for Optimizer Worker"
  default     = "asia-south1-docker.pkg.dev/zonepilot-prod-9a4285/zonepilot-containers-production/zonepilot-worker:latest"
}

variable "dispatcher_image" {
  type        = string
  description = "Container image URL for Outbox Dispatcher"
  default     = "asia-south1-docker.pkg.dev/zonepilot-prod-9a4285/zonepilot-containers-production/zonepilot-dispatcher:latest"
}

variable "release_sha" {
  type        = string
  description = "Source code Git SHA for release identity"
  default     = ""
}
