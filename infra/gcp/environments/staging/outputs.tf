output "api_url" {
  value = module.cloud_run.api_url
}

output "workload_identity_provider" {
  value = module.iam.workload_identity_provider
}

output "deployer_service_account" {
  value = module.iam.deployer_sa_email
}

output "artifact_registry_repo" {
  value = module.artifact_registry.repository_url
}

output "evidence_bucket" {
  value = module.storage.evidence_bucket_name
}

output "pubsub_topic" {
  value = module.pubsub.topic_name
}
