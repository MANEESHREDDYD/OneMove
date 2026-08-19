terraform {
  backend "gcs" {
    bucket = "zonepilot-production-artifacts-9a4285"
    prefix = "terraform/state"
  }
}
