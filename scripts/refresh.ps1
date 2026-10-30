param([string]$Python = "C:\Users\hp\portfolio-env\Scripts\python.exe", [switch]$Download, [switch]$LoadSql)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path "reports/local" | Out-Null
Start-Transcript -Path "reports/local/refresh.log" -Append
try {
    if ($Download) { & $Python -m multi_asset.pipeline --download }
    else { & $Python -m multi_asset.pipeline }
    if ($LASTEXITCODE -ne 0) { throw "Research pipeline failed" }
    if ($LoadSql) {
        & $Python -m multi_asset.database
        if ($LASTEXITCODE -ne 0) { throw "SQL Server load failed" }
    }
} finally { Stop-Transcript }
