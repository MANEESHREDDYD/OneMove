# GCP Safety Guard for ZonePilot Infrastructure Operations
# Rejects non-zonepilot projects and explicitly aborts if signit-502902 is active.

$ErrorActionPreference = "Stop"

$activeProject = (gcloud config get-value project 2>$null).Trim()

if (-not $activeProject) {
    Write-Error "ABORT: No active GCP project configured."
    exit 1
}

if ($activeProject -eq "signit-502902" -or $activeProject -eq "project-2040fcfb-596f-42ba-9c9") {
    Write-Error "CRITICAL SAFETY VIOLATION: Protected external project '$activeProject' is active. Aborting immediately."
    exit 1
}

if (-not ($activeProject -like "zonepilot-*")) {
    Write-Error "SAFETY ABORT: Active project '$activeProject' does not begin with 'zonepilot-'."
    exit 1
}

Write-Host "GCP Safety Guard: Verified active project is '$activeProject'."
