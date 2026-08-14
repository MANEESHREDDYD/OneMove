param (
    [string]$DataRoot = "C:\Users\md200\OneDrive\Desktop\OneMove\data_root",
    [string]$RepoRoot = "C:\Users\md200\OneDrive\Desktop\OneMove"
)

Write-Host "Setting up ZonePilot Data Acquisition Tasks in Windows Task Scheduler..."

# Action for Midnight Task
$MidnightAction = New-ScheduledTaskAction -Execute "python" -Argument "$RepoRoot\services\collectors\scheduler_midnight.py" -WorkingDirectory $RepoRoot
$MidnightTrigger = New-ScheduledTaskTrigger -Daily -At "00:00"
$MidnightSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "ZonePilot_Midnight_Acquisition" -Action $MidnightAction -Trigger $MidnightTrigger -Settings $MidnightSettings -Description "Runs ZonePilot midnight rollover and historical backfill at 00:00 IST." -Force

# Action for Intraday Task (every 15 minutes)
$IntradayAction = New-ScheduledTaskAction -Execute "python" -Argument "$RepoRoot\services\collectors\scheduler_intraday.py" -WorkingDirectory $RepoRoot
$IntradayTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
$IntradaySettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "ZonePilot_Intraday_Acquisition" -Action $IntradayAction -Trigger $IntradayTrigger -Settings $IntradaySettings -Description "Runs ZonePilot intraday live traffic and forecast snapshots every 15 minutes." -Force

Write-Host "Successfully registered ZonePilot_Midnight_Acquisition and ZonePilot_Intraday_Acquisition."
Write-Host "Note: Ensure your environment variables (TOMTOM_API_KEY, SWIGGY_*, ZONEPILOT_DATA_ROOT) are set at the system or user level so the background tasks can read them."
