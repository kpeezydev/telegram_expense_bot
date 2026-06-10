param(
    [string]$ServiceName = "expense-bot",
    [string]$Region = "us-central1"
)

gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 1 `
    --concurrency 80 `
    --cpu 1 `
    --memory 256Mi `
    --timeout 5m

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployed! Registering webhook..."
    python register_webhook.py
}
else {
    Write-Host "`nDeployment failed."
    exit 1
}
