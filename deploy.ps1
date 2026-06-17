param(
    [string]$ServiceName = "expense-bot",
    [string]$Region = "us-central1"
)

# Optional Grafana Cloud secrets (only set if you configured monitoring)
$grafanaSecrets = @()
if ($env:GRAFANA_CLOUD_PROM_URL) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_PROM_URL=expense-bot-grafana-prom-url:1"
}
if ($env:GRAFANA_CLOUD_PROM_USERNAME) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_PROM_USERNAME=expense-bot-grafana-prom-username:1"
}
if ($env:GRAFANA_CLOUD_PROM_PASSWORD) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_PROM_PASSWORD=expense-bot-grafana-prom-password:1"
}
if ($env:GRAFANA_CLOUD_LOKI_URL) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_LOKI_URL=expense-bot-grafana-loki-url:1"
}
if ($env:GRAFANA_CLOUD_LOKI_USERNAME) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_LOKI_USERNAME=expense-bot-grafana-loki-username:1"
}
if ($env:GRAFANA_CLOUD_LOKI_PASSWORD) {
    $grafanaSecrets += "--set-secrets=GRAFANA_CLOUD_LOKI_PASSWORD=expense-bot-grafana-loki-password:1"
}
if ($env:LOG_FORMAT) {
    $grafanaSecrets += "--set-secrets=LOG_FORMAT=expense-bot-log-format:1"
}
if ($env:SERVICE_NAME) {
    $grafanaSecrets += "--set-secrets=SERVICE_NAME=expense-bot-service-name:1"
}

gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 1 `
    --concurrency 80 `
    --cpu 1 `
    --memory 256Mi `
    --timeout 5m `
    @grafanaSecrets

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeployed! Registering webhook..."
    python register_webhook.py
}
else {
    Write-Host "`nDeployment failed."
    exit 1
}
