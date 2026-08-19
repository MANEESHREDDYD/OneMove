variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment (staging/production)"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository owner/name (MANEESHREDDYD/OneMove)"
  default     = "MANEESHREDDYD/OneMove"
}

# 1. API Service Account
resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "zonepilot-api-${var.environment}"
  display_name = "ZonePilot API Runtime (${var.environment})"
}

# 2. Worker Service Account
resource "google_service_account" "worker" {
  project      = var.project_id
  account_id   = "zonepilot-worker-${var.environment}"
  display_name = "ZonePilot Optimizer Worker (${var.environment})"
}

# 3. OSRM Service Account
resource "google_service_account" "osrm" {
  project      = var.project_id
  account_id   = "zonepilot-osrm-${var.environment}"
  display_name = "ZonePilot OSRM Engine (${var.environment})"
}

# 4. Acquisition Service Account
resource "google_service_account" "acquisition" {
  project      = var.project_id
  account_id   = "zonepilot-acq-${var.environment}"
  display_name = "ZonePilot Acquisition Collector (${var.environment})"
}

# 5. Dedicated Pub/Sub Push Invoker Service Account
resource "google_service_account" "pubsub_push" {
  project      = var.project_id
  account_id   = "onemove-pubsub-push-${var.environment}"
  display_name = "OneMove Pub/Sub Push Invoker (${var.environment})"
}

# 5b. Dedicated Outbox Dispatcher Service Account
resource "google_service_account" "dispatcher" {
  project      = var.project_id
  account_id   = "onemove-dispatcher-${var.environment}"
  display_name = "OneMove Outbox Dispatcher Runtime (${var.environment})"
}

# 6. GitHub Deployer Service Account (Workload Identity Federation)
resource "google_service_account" "github_deployer" {
  project      = var.project_id
  account_id   = "zonepilot-deployer-${var.environment}"
  display_name = "ZonePilot GitHub Actions Deployer (${var.environment})"
}

# Workload Identity Pool
resource "google_iam_workload_identity_pool" "github_pool" {
  project                   = var.project_id
  workload_identity_pool_id = "github-pool-${var.environment}"
  display_name              = "GitHub Actions Pool (${var.environment})"
}

# Workload Identity Provider
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider-${var.environment}"
  display_name                       = "GitHub Provider (${var.environment})"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Allow GitHub Actions to impersonate deployer SA
resource "google_service_account_iam_member" "github_impersonation" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repository}"
}

# Least Privilege IAM Roles for API SA
resource "google_project_iam_member" "api_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Least Privilege IAM Roles for Worker SA
resource "google_project_iam_member" "worker_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.subscriber",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# Least Privilege IAM Roles for Dispatcher SA
resource "google_project_iam_member" "dispatcher_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.publisher",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.dispatcher.email}"
}

# Least Privilege IAM Roles for Deployer SA
resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/run.developer",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_deployer.email}"
}

output "api_sa_email" {
  value = google_service_account.api.email
}

output "worker_sa_email" {
  value = google_service_account.worker.email
}

output "dispatcher_sa_email" {
  value = google_service_account.dispatcher.email
}

output "osrm_sa_email" {
  value = google_service_account.osrm.email
}

output "acquisition_sa_email" {
  value = google_service_account.acquisition.email
}

output "pubsub_push_sa_email" {
  value = google_service_account.pubsub_push.email
}

output "deployer_sa_email" {
  value = google_service_account.github_deployer.email
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github_provider.name
}
