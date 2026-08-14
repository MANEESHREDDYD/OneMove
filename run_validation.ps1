$ErrorActionPreference = "Continue"

function Run-AuditCommand {
    param([string]$cmd)
    
    $startTime = Get-Date
    "---" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    "Timestamp: $($startTime.ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    "Command: $cmd" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    
    try {
        $output = Invoke-Expression $cmd 2>&1
        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) { $exitCode = 0 }
    } catch {
        $output = $_.Exception.Message
        $exitCode = 1
    }
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    "Exit Code: $exitCode" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    "Duration: ${duration}s" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    "Output:`n$output" | Out-File -Append "reports/pre_zonepilot_audit/COMMAND_LOG.txt"
    
    Write-Host "Finished $cmd with exit code $exitCode in ${duration}s"
}

$commands = @(
    "npm run validate:env",
    "npm run lint",
    "npm run typecheck",
    "npm run test",
    "npm run build",
    "npm run test:backend",
    "npm run test:ml",
    "npm run test:contracts",
    "npm run test:property",
    "npm run audit:ui",
    "npm run audit:details",
    "npm run verify:supabase",
    "npm run test:supabase",
    "npm run test:rls",
    "npm run verify:demo-depth",
    "npm run pipeline:all",
    "npm run analytics:refresh",
    "npm run intelligence:refresh",
    "npm run py:install",
    "npm run py:lint",
    "npm run py:test",
    "npm run py:dq",
    "npm run py:features",
    "npm run py:analytics",
    "npm run py:ml",
    "npm run py:evaluate",
    "npm run java:build",
    "npm run java:test",
    "npm run c:build",
    "npm run c:test",
    "npm run c:benchmark",
    "npm run test:e2e",
    "npm run test:performance:local",
    "npm run healthcheck"
)

foreach ($c in $commands) {
    Run-AuditCommand -cmd $c
}
