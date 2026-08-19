terraform {
  backend "gcs" {
    bucket = "zonepilot-staging-artifacts-9a4285"
    prefix = "terraform/state"
  }
}
