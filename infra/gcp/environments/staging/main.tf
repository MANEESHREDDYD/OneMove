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
  environment       = "staging"
  github_repository = "MANEESHREDDYD/OneMove"
  depends_on        = [module.services]
}

# 3. Artifact Registry
module "artifact_registry" {
  source      = "../../modules/artifact_registry"
  project_id  = var.project_id
  region      = var.region
  environment = "staging"
  depends_on  = [module.services]
}

# 4. Cloud Storage
module "storage" {
  source        = "../../modules/storage"
  project_id    = var.project_id
  region        = var.region
  environment   = "staging"
  unique_suffix = var.unique_suffix
  depends_on    = [module.services]
}

# 5. Secret Manager
module "secrets" {
  source      = "../../modules/secrets"
  project_id  = var.project_id
  environment = "staging"
  depends_on  = [module.services]
}

# 6. Cloud Run Services
module "cloud_run" {
  source               = "../../modules/cloud_run"
  project_id           = var.project_id
  region               = var.region
  environment          = "staging"
  release_sha          = var.release_sha
  api_image            = var.api_image
  worker_image         = var.worker_image
  dispatcher_image     = var.dispatcher_image
  api_sa_email         = module.iam.api_sa_email
  worker_sa_email      = module.iam.worker_sa_email
  dispatcher_sa_email  = module.iam.dispatcher_sa_email
  pubsub_push_sa_email = module.iam.pubsub_push_sa_email
  depends_on           = [module.services, module.iam, module.secrets]
}

# 7. Pub/Sub Async Queue & Dead-Letter with Authenticated Push Config
module "pubsub" {
  source                     = "../../modules/pubsub"
  project_id                 = var.project_id
  environment                = "staging"
  push_endpoint              = "${module.cloud_run.worker_url}/push"
  push_service_account_email = module.iam.pubsub_push_sa_email
  depends_on                 = [module.services, module.cloud_run]
}

# 8. Monitoring & Alerts
module "monitoring" {
  source      = "../../modules/monitoring"
  project_id  = var.project_id
  environment = "staging"
  depends_on  = [module.services]
}

# 9. Cloud Billing Budget
module "budgets" {
  source          = "../../modules/budgets"
  billing_account = var.billing_account
  project_id      = var.project_id
  environment     = "staging"
  budget_amount   = 50
  depends_on      = [module.services]
}
