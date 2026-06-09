import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    """Initialize and return the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def add_expense(user_id: int, description: str, amount: float, expense_date: str) -> dict:
    """Insert a new expense into Supabase."""
    supabase = get_supabase()
    data = {
        "user_id": user_id,
        "description": description,
        "amount": amount,
        "date": expense_date
    }
    # Assumes a table named 'expenses' exists
    response = supabase.table("expenses").insert(data).execute()
    return response.data

def get_total_expenses_for_month(user_id: int, year: int, month: int) -> float:
    """Calculate the total expenses for a specific user and month."""
    supabase = get_supabase()
    
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"

    # Fetch rows in the date range
    response = supabase.table("expenses") \
        .select("amount") \
        .eq("user_id", user_id) \
        .gte("date", start_date) \
        .lt("date", end_date) \
        .execute()
    
    total = sum(item['amount'] for item in response.data)
    return total

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
    supabase = get_supabase()
    # Add one day to end_date so the range is inclusive
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    end_exclusive = end.strftime("%Y-%m-%d")

    response = supabase.table("expenses") \
        .select("*") \
        .eq("user_id", user_id) \
        .gte("date", start_date) \
        .lt("date", end_exclusive) \
        .order("date") \
        .execute()

    return response.data
