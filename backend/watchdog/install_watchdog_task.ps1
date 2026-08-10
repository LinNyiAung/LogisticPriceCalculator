<#
.SYNOPSIS
    Registers watchdog.ps1 to run every 1 minute via Windows Task Scheduler.
    Run this ONCE, as Administrator, from the same folder as watchdog.ps1.
#>

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$WatchdogPs1 = Join-Path $ScriptDir "watchdog.ps1"
$TaskName   = "LogCalculatorWatchdog"

if (-not (Test-Path $WatchdogPs1)) {
    Write-Error "watchdog.ps1 not found next to this script at: $WatchdogPs1"
    exit 1
}

$Action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WatchdogPs1`""

$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Remove any partially-created task from a previous failed run
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
        -Principal $Principal -Settings $Settings -Force -ErrorAction Stop

    Write-Host "Scheduled task '$TaskName' registered - runs every 1 minute as SYSTEM."
    Write-Host "Edit watchdog.ps1's `$ServiceName parameter to match your actual NSSM service name before relying on this."
} catch {
    Write-Error "Failed to register scheduled task: $($_.Exception.Message)"
    exit 1
}
