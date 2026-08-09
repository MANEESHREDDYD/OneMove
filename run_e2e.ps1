$ErrorActionPreference = "Continue"

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

Write-Host "=== ZonePilot Portable E2E Test Runner ==="

# 1. Obtain Supabase credentials dynamically if available, or fallback to .env.local
if (Test-Path ".env.local") {
    Get-Content ".env.local" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line.Split('=', 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $val = $parts[1].Trim().Trim('"')
                if ($key -eq "NEXT_PUBLIC_SUPABASE_URL") { $env:SUPABASE_URL = $val }
                if ($key -eq "NEXT_PUBLIC_SUPABASE_ANON_KEY") { $env:SUPABASE_ANON_KEY = $val }
                if ($key -eq "SUPABASE_SERVICE_ROLE_KEY") { $env:SUPABASE_SERVICE_ROLE_KEY = $val }
            }
        }
    }
}

# Try Supabase CLI dynamically if running
try {
    $statusOutput = npx supabase status -o json 2>$null | Out-String
    if ($statusOutput -and $statusOutput.StartsWith("{")) {
        $statusJson = $statusOutput | ConvertFrom-Json
        if ($statusJson.API_URL) { $env:SUPABASE_URL = $statusJson.API_URL }
        if ($statusJson.ANON_KEY) { $env:SUPABASE_ANON_KEY = $statusJson.ANON_KEY }
        if ($statusJson.SERVICE_ROLE_KEY) { $env:SUPABASE_SERVICE_ROLE_KEY = $statusJson.SERVICE_ROLE_KEY }
    }
} catch {
    Write-Host "Local Supabase CLI not active, using default environment configuration."
}

# 2. Launch FastAPI backend locally on port 8000
$env:PYTHONPATH = "$repoRoot/services/api"
$backendProc = Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" -WorkingDirectory "$repoRoot/services/api" -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

try {
    Write-Host "Running Marketplace Probe E2E test..."
    npx playwright test apps/observatory/tests/e2e/marketplace_probe_offline.spec.ts --project=chromium
    
    Write-Host "Running Volunteer Order E2E test..."
    npx playwright test apps/observatory/tests/e2e/volunteer_order_offline.spec.ts --project=chromium
} finally {
    # Clean termination of specific process started
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
}
