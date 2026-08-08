cd C:\Users\md200\OneDrive\Desktop\OneMove\services\api
Stop-Process -Name "python" -ErrorAction SilentlyContinue
Stop-Process -Name "node" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_ANON_KEY = "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"

Start-Process -FilePath "C:\Users\md200\AppData\Local\Programs\Python\Python311\python.exe" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" -RedirectStandardOutput "uvicorn.log" -RedirectStandardError "uvicorn_err.log" -WindowStyle Hidden
Start-Sleep -Seconds 3

cd C:\Users\md200\OneDrive\Desktop\OneMove\apps\observatory
npx playwright test tests/e2e/offline.spec.ts --project=chromium

# Cleanup
Stop-Process -Name "python" -ErrorAction SilentlyContinue
Stop-Process -Name "node" -ErrorAction SilentlyContinue
