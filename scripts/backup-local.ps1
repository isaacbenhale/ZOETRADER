param(
    [string]$Database = "data/trading.db",
    [string]$ConfigDir = "config",
    [string]$Destination = "backups/latest"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
if (Test-Path $Database) {
    Copy-Item $Database -Destination $Destination -Force
}
if (Test-Path $ConfigDir) {
    Copy-Item $ConfigDir -Destination $Destination -Recurse -Force
}
Write-Host "Backup completed: $Destination"

