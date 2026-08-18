terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

# 1. Project Services
module "services" {
  source     = "../../modules/project_services"
  project_id = var.project_id
}

# 2. IAM & Workload Identity Federation
module "iam" {
  source            = "../../modules/iam"
  project_id        = var.project_id
  environment       = "production"
  github_repository = "MANEESHREDDYD/OneMove"
  depends_on        = [module.services]
}

# 3. Artifact Registry
module "artifact_registry" {
  source      = "../../modules/artifact_registry"
  project_id  = var.project_id
  region      = var.region
  environment = "production"
  depends_on  = [module.services]
}

# 4. Cloud Storage
module "storage" {
  source        = "../../modules/storage"
  project_id    = var.project_id
  region        = var.region
  environment   = "production"
  unique_suffix = var.unique_suffix
  depends_on    = [module.services]
}

# 5. Pub/Sub Async Queue & Dead-Letter
module "pubsub" {
  source      = "../../modules/pubsub"
  project_id  = var.project_id
  environment = "production"
  depends_on  = [module.services]
}

# 6. Secret Manager
module "secrets" {
  source      = "../../modules/secrets"
  project_id  = var.project_id
  environment = "production"
  depends_on  = [module.services]
}

# 7. Cloud Run Services
module "cloud_run" {
  source          = "../../modules/cloud_run"
  project_id      = var.project_id
  region          = var.region
  environment     = "production"
  api_image       = var.api_image
  worker_image    = var.worker_image
  api_sa_email    = module.iam.api_sa_email
  worker_sa_email = module.iam.worker_sa_email
  depends_on      = [module.services, module.iam]
}

# 8. Monitoring & Alerts
module "monitoring" {
  source      = "../../modules/monitoring"
  project_id  = var.project_id
  environment = "production"
  depends_on  = [module.services]
}

# 9. Cloud Billing Budget
module "budgets" {
  source          = "../../modules/budgets"
  billing_account = var.billing_account
  project_id      = var.project_id
  environment     = "production"
  budget_amount   = 100
  depends_on      = [module.services]
}
