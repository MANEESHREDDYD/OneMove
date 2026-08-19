variable "project_id" {
  type        = string
  description = "Staging GCP Project ID"
  default     = "zonepilot-stg-9a4285"
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
  default     = "asia-south1-docker.pkg.dev/zonepilot-stg-9a4285/zonepilot-containers-staging/zonepilot-api:latest"
}

variable "worker_image" {
  type        = string
  description = "Container image URL for Optimizer Worker"
  default     = "asia-south1-docker.pkg.dev/zonepilot-stg-9a4285/zonepilot-containers-staging/zonepilot-worker:latest"
}
