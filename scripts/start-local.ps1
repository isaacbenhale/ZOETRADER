param(
    [ValidateSet("bootstrap", "healthcheck", "scan", "backtest", "ui", "approve-loop")]
    [string]$Action = "scan",
    [string]$Mode = "MONITORING",
    [string]$ConfigDir = "config",
    [double]$Equity = 10000,
    [string]$JournalDb = "data/trading.db",
    [string]$StatusFile = "data/zoetrading_status.csv",
    [string]$CommandFile = "data/zoetrading_command.csv",
    [int]$CandleCount = 500,
    [int]$LookaheadBars = 20,
    [string]$ReportFile = "data/backtest_report.json",
    [string]$UiHost = "127.0.0.1",
    [int]$UiPort = 8765,
    [double]$ApprovalTimeout = 120,
    [double]$PollInterval = 1
)

$ErrorActionPreference = "Stop"
Write-Host "zoeTrading local action: $Action"

if ($Action -eq "bootstrap") {
    python -m zoetrading.main bootstrap --mode $Mode --config-dir $ConfigDir
}
elseif ($Action -eq "healthcheck") {
    python -m zoetrading.main healthcheck --config-dir $ConfigDir --journal-db $JournalDb
}
elseif ($Action -eq "backtest") {
    python -m zoetrading.main backtest --config-dir $ConfigDir --journal-db $JournalDb --candle-count $CandleCount --lookahead-bars $LookaheadBars --report-file $ReportFile
}
elseif ($Action -eq "ui") {
    python -m zoetrading.main ui --config-dir $ConfigDir --journal-db $JournalDb --status-file $StatusFile --report-file $ReportFile --host $UiHost --port $UiPort
}
elseif ($Action -eq "approve-loop") {
    python -m zoetrading.main approve-loop --config-dir $ConfigDir --journal-db $JournalDb --status-file $StatusFile --command-file $CommandFile --equity $Equity --approval-timeout $ApprovalTimeout --poll-interval $PollInterval
}
else {
    python -m zoetrading.main scan-once --mode $Mode --equity $Equity --config-dir $ConfigDir --journal-db $JournalDb --status-file $StatusFile
}
