cd C:\Users\md200\OneDrive\Desktop\OneMove\services\api
Stop-Process -Name "python" -ErrorAction SilentlyContinue
Stop-Process -Name "node" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$statusJson = npx supabase status -o json | Out-String | ConvertFrom-Json
$env:SUPABASE_URL = $statusJson.API_URL
$env:SUPABASE_ANON_KEY = $statusJson.ANON_KEY
$env:SUPABASE_SERVICE_ROLE_KEY = $statusJson.SERVICE_ROLE_KEY
if (-not $env:SUPABASE_ANON_KEY) {
    Write-Error "Failed to retrieve Supabase keys. Make sure Supabase is running."
    exit 1
}

Start-Process -FilePath "C:\Users\md200\AppData\Local\Programs\Python\Python311\python.exe" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" -RedirectStandardOutput "uvicorn.log" -RedirectStandardError "uvicorn_err.log" -WindowStyle Hidden
Start-Sleep -Seconds 3

cd C:\Users\md200\OneDrive\Desktop\OneMove\apps\observatory
npx playwright test tests/e2e/offline.spec.ts --project=chromium

# Cleanup
Stop-Process -Name "python" -ErrorAction SilentlyContinue
Stop-Process -Name "node" -ErrorAction SilentlyContinue
