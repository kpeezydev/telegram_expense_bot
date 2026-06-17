import os
import time
import logging
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

import metrics

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    """Initialize and return the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def add_expenses_batch(user_id: int, expenses: list) -> list:
    """Insert multiple expenses in a single batch call.
    Each expense dict must have 'description', 'amount', 'date' keys."""
    supabase = get_supabase()
    rows = []
    for exp in expenses:
        rows.append({
            "user_id": user_id,
            "description": exp["description"],
            "amount": exp["amount"],
            "date": exp["date"]
        })
    response = supabase.table("expenses").insert(rows).execute()
    return response.data


def add_expense(user_id: int, description: str, amount: float, expense_date: str) -> dict:
    """Insert a new expense into Supabase."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        data = {
            "user_id": user_id,
            "description": description,
            "amount": amount,
            "date": expense_date
        }
        response = supabase.table("expenses").insert(data).execute()
        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="add_expense").observe(duration)
        logger.info("Supabase add_expense completed", extra={"duration_ms": round(duration * 1000, 2)})
        return response.data
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase add_expense failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise

def get_total_expenses_for_month(user_id: int, year: int, month: int) -> float:
    """Calculate the total expenses for a specific user and month."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"

        response = supabase.table("expenses") \
            .select("amount") \
            .eq("user_id", user_id) \
            .gte("date", start_date) \
            .lt("date", end_date) \
            .execute()

        total = sum(item['amount'] for item in response.data)
        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="get_total").observe(duration)
        logger.info("Supabase get_total completed", extra={"duration_ms": round(duration * 1000, 2)})
        return total
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase get_total failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise

def get_expenses_for_month(user_id: int, year: int, month: int) -> list:
    """Retrieve all expenses for a specific user and month."""
    supabase = get_supabase()
    
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"

    response = supabase.table("expenses") \
        .select("*") \
        .eq("user_id", user_id) \
        .gte("date", start_date) \
        .lt("date", end_date) \
        .order("date") \
        .execute()
    
    return response.data

def get_expenses_in_range(user_id: int, start_date: str, end_date: str) -> list:
    """Retrieve all expenses for a user within a date range (inclusive)."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        end_exclusive = end.strftime("%Y-%m-%d")

        response = supabase.table("expenses") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", start_date) \
            .lt("date", end_exclusive) \
            .order("date") \
            .execute()

        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="get_expenses").observe(duration)
        logger.info("Supabase get_expenses completed", extra={"duration_ms": round(duration * 1000, 2)})
        return response.data
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase get_expenses failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise


def find_expenses_by_match(user_id: int, description: str = None, amount: float = None,
                           expense_date: str = None) -> list:
    """Find expenses matching the given criteria for a user.
    All params except user_id are optional — only provided ones are used as filters."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        query = supabase.table("expenses").select("*").eq("user_id", user_id)
        if description:
            query = query.ilike("description", f"%{description}%")
        if amount is not None:
            query = query.eq("amount", amount)
        if expense_date:
            query = query.eq("date", expense_date)
        response = query.order("date").execute()
        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="get_expenses").observe(duration)
        logger.info("Supabase find_expenses completed", extra={"duration_ms": round(duration * 1000, 2)})
        return response.data
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase find_expenses failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise


def delete_expense_by_id(user_id: int, expense_id: int) -> bool:
    """Delete an expense by ID, scoped to the given user. Returns True if deleted."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        response = supabase.table("expenses") \
            .delete() \
            .eq("id", expense_id) \
            .eq("user_id", user_id) \
            .execute()
        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="delete_expense").observe(duration)
        logger.info("Supabase delete_expense completed", extra={"duration_ms": round(duration * 1000, 2)})
        return len(response.data) > 0
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase delete_expense failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise


def delete_expense(expense_id: int) -> bool:
    """Low-level delete by ID without user scoping. Returns True if deleted."""
    start = time.monotonic()
    try:
        supabase = get_supabase()
        response = supabase.table("expenses") \
            .delete() \
            .eq("id", expense_id) \
            .execute()
        duration = time.monotonic() - start
        metrics.bot_supabase_duration_seconds.labels(operation="delete_expense").observe(duration)
        logger.info("Supabase delete_expense completed", extra={"duration_ms": round(duration * 1000, 2)})
        return len(response.data) > 0
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Supabase delete_expense failed: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="supabase_client", exception_type=type(e).__name__).inc()
        raise
