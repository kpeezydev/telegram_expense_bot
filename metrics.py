import os
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

SERVICE_NAME = os.getenv("SERVICE_NAME", "expense-bot")

bot_requests_total = Counter(
    "bot_requests_total",
    "Total number of bot requests by handler and status",
    ["handler", "status"],
)

bot_request_duration_seconds = Histogram(
    "bot_request_duration_seconds",
    "Request duration in seconds by handler",
    ["handler"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5, 5),
)

bot_errors_total = Counter(
    "bot_errors_total",
    "Total number of caught exceptions by module and exception type",
    ["module", "exception_type"],
)

bot_active_users = Gauge(
    "bot_active_users",
    "Number of unique users who have started the bot in this process lifetime",
)

bot_gemini_duration_seconds = Histogram(
    "bot_gemini_duration_seconds",
    "Duration of Gemini NLU parse calls in seconds",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10),
)

bot_supabase_duration_seconds = Histogram(
    "bot_supabase_duration_seconds",
    "Duration of Supabase queries in seconds by operation",
    ["operation"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5),
)


def get_metrics():
    return generate_latest(REGISTRY)
