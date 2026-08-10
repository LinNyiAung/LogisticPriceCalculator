<#
.SYNOPSIS
    Health-check watchdog for the LogCalculator app running under NSSM.

.DESCRIPTION
    Hits the app's /health endpoint. If it doesn't respond with HTTP 200
    within the timeout, restarts the NSSM service. This exists because
    NSSM only restarts a service when the PROCESS exits - it can't detect
    a "zombie" state where the process is alive but has stopped accepting
    new connections (which is what happened on 2026-08-08: an unhandled
    OSError killed the asyncio accept loop without killing the process).

.NOTES
    Intended to run every 1-2 minutes via Windows Task Scheduler.
    Logs to watchdog.log next to this script.
#>

param(
    [string]$ServiceName = "LogisticCostCalculator",   # <-- CHANGE to your actual NSSM service name
    [string]$HealthUrl    = "http://localhost:8000/health",
    [int]$TimeoutSeconds  = 10,
    [int]$FailureThreshold = 2                    # consecutive failures before restarting
)

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile     = Join-Path $ScriptDir "watchdog.log"
$StateFile   = Join-Path $ScriptDir "watchdog_state.txt"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $Message" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

# Read consecutive-failure count from state file (created fresh if missing)
$failCount = 0
if (Test-Path $StateFile) {
    $raw = Get-Content $StateFile -Raw -ErrorAction SilentlyContinue
    if ($raw -and [int]::TryParse($raw.Trim(), [ref]$failCount) -eq $false) {
        $failCount = 0
    }
}

$isHealthy = $false
try {
    $response = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec $TimeoutSeconds -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $isHealthy = $true
    }
} catch {
    Write-Log "Health check failed: $($_.Exception.Message)"
}

if ($isHealthy) {
    if ($failCount -gt 0) {
        Write-Log "App recovered after $failCount failed check(s)."
    }
    "0" | Out-File -FilePath $StateFile -Encoding utf8
    exit 0
}

$failCount++
"$failCount" | Out-File -FilePath $StateFile -Encoding utf8
Write-Log "App unresponsive. Consecutive failures: $failCount / $FailureThreshold"

if ($failCount -ge $FailureThreshold) {
    Write-Log "Threshold reached - restarting NSSM service '$ServiceName'."
    try {
        & nssm restart $ServiceName
        Write-Log "Restart command issued for '$ServiceName'."
    } catch {
        Write-Log "ERROR: Failed to restart service - $($_.Exception.Message)"
    }
    "0" | Out-File -FilePath $StateFile -Encoding utf8
}
