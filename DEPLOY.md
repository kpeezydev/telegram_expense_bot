# Deploy to Google Cloud Run

## Prerequisites

- [Google Cloud SDK (`gcloud`) installed](https://cloud.google.com/sdk/docs/install)
- A [GCP project](https://console.cloud.google.com/) with billing enabled (you won't be charged — bot fits in free tier)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed (needed for `gcloud run deploy --source`)
- All env vars in `.env` filled out

---

## Step 1: Enable required GCP services

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

---

## Step 2: Generate a webhook secret token

This token lets the bot verify that incoming webhook requests actually come from Telegram.

```powershell
# Generate a random 32-byte hex string
python -c "import secrets; print(secrets.token_hex(32))"
```

Add it to `.env`:

```ini
SECRET_TOKEN=<the-output-above>
```

---

## Step 3: Store env vars in Secret Manager (first time only)

Sensitive values (tokens, keys) are stored in Secret Manager and referenced by Cloud Run — never exposed as plaintext.

```powershell
# Compute Engine default service account
$SA = "$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

# Create secrets and grant access
foreach ($pair in @(
    @{name="expense-bot-telegram-token"; value=$env:TELEGRAM_BOT_TOKEN}
    @{name="expense-bot-secret-token"; value=$env:SECRET_TOKEN}
    @{name="expense-bot-gemini-key"; value=$env:GEMINI_API_KEY}
    @{name="expense-bot-supabase-url"; value=$env:SUPABASE_URL}
    @{name="expense-bot-supabase-key"; value=$env:SUPABASE_KEY}
    @{name="expense-bot-allowed-users"; value=$env:ALLOWED_USER_IDS}
)) {
    Set-Content -Path "$env:TEMP\$($pair.name).txt" -NoNewline -Value $pair.value
    gcloud secrets create $pair.name --data-file="$env:TEMP\$($pair.name).txt" --quiet
    gcloud secrets add-iam-policy-binding $pair.name `
        --member="serviceAccount:$SA" `
        --role="roles/secretmanager.secretAccessor" `
        --quiet
    Remove-Item "$env:TEMP\$($pair.name).txt"
}
```

---

## Step 4: First deploy

```powershell
gcloud run deploy expense-bot --source . --region us-central1 --allow-unauthenticated `
  --min-instances 0 --max-instances 1 --concurrency 80 --cpu 1 --memory 256Mi --timeout 5m `
  --set-secrets=TELEGRAM_BOT_TOKEN=expense-bot-telegram-token:1 `
  --set-secrets=SECRET_TOKEN=expense-bot-secret-token:1 `
  --set-secrets=GEMINI_API_KEY=expense-bot-gemini-key:1 `
  --set-secrets=SUPABASE_URL=expense-bot-supabase-url:1 `
  --set-secrets=SUPABASE_KEY=expense-bot-supabase-key:1 `
  --set-secrets=ALLOWED_USER_IDS=expense-bot-allowed-users:1
```

Wait for the command to finish. It prints something like:

```
Service [expense-bot] Revision [...] URL: https://expense-bot-xxxxx-uc.a.run.app
```

---

## Step 5: Set WEBHOOK_URL in .env

```ini
WEBHOOK_URL=https://expense-bot-xxxxx-uc.a.run.app
```

---

## Step 6: Register the webhook with Telegram

```powershell
python register_webhook.py
```

---

## Step 7: Verify it works

Send a message to your bot on Telegram. The first message after idle takes 2–5 seconds (cold start).

Check webhook status:

```powershell
python -c "import requests; r = requests.get('https://api.telegram.org/bot<TOKEN>/getWebhookInfo').json(); print(r)"
```

---

## Step 8: Set up Grafana Cloud monitoring (optional)

The bot exposes Prometheus metrics at `/metrics` and supports structured JSON logging. Grafana Cloud free tier is recommended.

### 8a. Sign up for Grafana Cloud

1. Go to [grafana.com](https://grafana.com) and sign up for the **Free** tier
2. Create a **Grafana** stack and a **Prometheus** data source
3. Note your **Instance ID**, **API Key**, and **Prometheus remote write endpoint** (URL ending in `/api/prom/push`)

### 8b. Configure Prometheus scraping

Grafana Cloud can scrape the Cloud Run `/metrics` endpoint:

**Option A — Grafana Cloud Prometheus scrape job (simplest):**
```
scrape_configs:
  - job_name: 'expense-bot'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['expense-bot-xxxxx-uc.a.run.app']
    scheme: https
```

**Option B — Prometheus remote write (requires the bot to push):**
Set the `GRAFANA_CLOUD_PROM_URL`, `GRAFANA_CLOUD_PROM_USERNAME`, and `GRAFANA_CLOUD_PROM_PASSWORD` env vars on Cloud Run. (The bot does not currently push — this is reserved for future use.)

### 8c. Connect Cloud Run logs to Loki

Use Grafana's **Google Cloud Logging** data source (pull model):

1. In Grafana Cloud, add a **Google Cloud Logging** data source
2. Create a GCP service account with `roles/logging.viewer` on your project
3. Download the service account key and upload it to Grafana Cloud
4. Your Cloud Run logs now appear in **Explore** with the Loki data source

### 8d. Import the dashboard

1. In Grafana, go to **Dashboards → Import**
2. Upload `grafana/dashboards/bot-overview.json` from this repository
3. Select your Prometheus data source when prompted
4. The dashboard panels will populate as metrics arrive

### 8e. Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_FORMAT` | No | plain-text | Set to `json` for structured JSON logs |
| `SERVICE_NAME` | No | `expense-bot` | Service identifier in logs and metrics |
| `GRAFANA_CLOUD_PROM_URL` | No | — | Grafana Cloud Prometheus remote write endpoint |
| `GRAFANA_CLOUD_PROM_USERNAME` | No | — | Grafana Cloud Prometheus username (instance ID) |
| `GRAFANA_CLOUD_PROM_PASSWORD` | No | — | Grafana Cloud Prometheus API key |
| `GRAFANA_CLOUD_LOKI_URL` | No | — | Grafana Cloud Loki push endpoint |
| `GRAFANA_CLOUD_LOKI_USERNAME` | No | — | Grafana Cloud Loki username (instance ID) |
| `GRAFANA_CLOUD_LOKI_PASSWORD` | No | — | Grafana Cloud Loki API key |

---

## Redeploying after changes

Env vars are preserved by Cloud Run, so future deploys are one command:

```powershell
.\deploy.ps1
```

Or manually:

```powershell
gcloud run deploy expense-bot --source . --region us-central1 --allow-unauthenticated
```

---

## Rolling back

```powershell
gcloud run revisions list --service expense-bot --region us-central1
gcloud run services update-traffic expense-bot --to-revisions=REVISION_NAME=100 --region us-central1
```

---

## Tearing down

```powershell
gcloud run services delete expense-bot --region us-central1
```

To switch back to local polling, just unset or remove `WEBHOOK_URL` from `.env` and run `python main.py` as before.
