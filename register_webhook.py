import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN is not set.")
    sys.exit(1)

url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("WEBHOOK_URL")

if not url:
    print("Usage: python register_webhook.py <CLOUD_RUN_URL>")
    print("       or set WEBHOOK_URL in .env")
    sys.exit(1)

webhook_url = f"{url.rstrip('/')}/webhook"

payload = {"url": webhook_url}
if SECRET_TOKEN:
    payload["secret_token"] = SECRET_TOKEN

api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
resp = requests.post(api_url, json=payload)
data = resp.json()

if data.get("ok"):
    print(f"✅ Webhook registered: {webhook_url}")
else:
    print(f"❌ Failed: {data}")
    sys.exit(1)

# Verify
verify = requests.get(
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
).json()
print(f"Current webhook: {verify.get('result', {}).get('url', 'none')}")
