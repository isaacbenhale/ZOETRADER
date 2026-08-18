param(
    [string]$Mode = "MONITORING",
    [string]$ConfigDir = "config"
)

$ErrorActionPreference = "Stop"
Write-Host "Starting zoeTrading locally in $Mode mode"
python -m zoetrading.main --mode $Mode --config-dir $ConfigDir

