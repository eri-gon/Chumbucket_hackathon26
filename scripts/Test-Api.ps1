# Test deployed API (hello). Base URL matches VITE_API_URL.
# Repo root:  pwsh -File .\scripts\Test-Api.ps1

$ErrorActionPreference = "Stop"
$BaseUrl = "https://1mgjr3yfea.execute-api.us-west-1.amazonaws.com/Prod"
$HelloUrl = "$BaseUrl/hello"

Write-Host "`nGET $HelloUrl" -ForegroundColor Cyan
(Invoke-RestMethod -Uri $HelloUrl -Method Get) | ConvertTo-Json -Compress
Write-Host "OK" -ForegroundColor Green
