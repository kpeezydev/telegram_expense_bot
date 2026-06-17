import os
import json
import time
import logging
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

import metrics

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

def parse_user_message(message: str) -> dict:
    """Parses a user message using the new google-genai SDK."""
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set.")
        return {"intent": "unknown"}
        
    start = time.monotonic()
    try:
        # Initialize Google GenAI client
        client = genai.Client(api_key=api_key)

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year
        
        system_instruction = f"""
You are a helpful expense tracker assistant. Your job is to parse the user's message and return a strictly valid JSON object.
Today's date is: {current_date}
The current year is: {current_year}

The user will either:
1. Provide one or more expenses. Messages can contain multiple expenses separated by newlines, numbered lists, bullet lists, or commas (e.g., "tuna - $10 - June 1\ncheese - $5 - June 2", "1. milk $3 2. bread $2", "coffee $5 today, lunch $15 yesterday").
2. Ask for the total expense (e.g., "total expense", "how much did I spend this month?").
3. Ask to list expenses within a timeframe (e.g., "show me my expenses this week", "list expenses from June 1 to June 15", "what did I spend last month?").
4. Ask to delete an expense (e.g., "delete expense test - $100 - Jun 10", "delete the tuna I bought for $5 last June 6", "delete expense #3").

Determine the intent and extract information.

Possible intents:
- "add_expenses"
- "get_total"
- "list_expenses"
- "delete_expense"
- "unknown"

If intent is "add_expenses", provide:
- "expenses": A JSON array of expense objects. Each object must have:
  - "description": A short string describing what the expense was.
  - "amount": A float representing the amount spent.
  - "date": A string in "YYYY-MM-DD" format. Infer the date if they use words like "today", "yesterday", or just a month/day based on the current year. If no date is provided, assume today.
Even if only one expense is detected, still return it as a single-element array.

If intent is "get_total", you don't need to provide description, amount, or date.

If intent is "list_expenses", provide:
- "start_date": A string in "YYYY-MM-DD" format representing the start of the requested timeframe.
- "end_date": A string in "YYYY-MM-DD" format representing the end of the requested timeframe.

If intent is "delete_expense", provide:
- "description": The description of the expense to delete (if mentioned).
- "amount": The amount of the expense to delete (if mentioned).
- "date": The date of the expense to delete (if mentioned, in YYYY-MM-DD format).
- "id": The numeric ID of the expense to delete (if the user references an ID like "#3" or "expense 3").

Extract whatever fields the user provides. The user may reference an expense by ID (e.g., "delete expense #3"), by a combination of description + amount + date (e.g., "delete lunch - $15 - yesterday"), or by description alone (e.g., "delete the tuna expense"). Only populate the fields the user explicitly mentions.

Resolve relative time expressions based on today's date ({current_date}):
- "this week": Monday through Sunday of the current week.
- "this month": First through last day of the current month.
- "last week": Monday through Sunday of the previous week.
- "last month": First through last day of the previous month.
- "from X to Y" or "between X and Y": Use the explicit dates provided.
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=f"User Message: {message}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                # Define structured schema to ensure we get exact key output structure
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "intent": {
                            "type": "STRING", 
                            "enum": ["add_expenses", "get_total", "list_expenses", "delete_expense", "unknown"]
                        },
                        "data": {
                            "type": "OBJECT",
                            "properties": {
                                "description": {"type": "STRING"},
                                "amount": {"type": "NUMBER"},
                                "date": {"type": "STRING"},
                                "expenses": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "description": {"type": "STRING"},
                                            "amount": {"type": "NUMBER"},
                                            "date": {"type": "STRING"}
                                        }
                                    }
                                },
                                "start_date": {"type": "STRING"},
                                "end_date": {"type": "STRING"},
                                "id": {"type": "INTEGER"}
                            }
                        }
                    },
                    "required": ["intent"]
                }
            )
        )
        
        result_text = response.text
        result_json = json.loads(result_text)
        duration = time.monotonic() - start
        metrics.bot_gemini_duration_seconds.observe(duration)
        logger.info("Gemini parse completed", extra={"duration_ms": round(duration * 1000, 2)})
        return result_json

    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"Error parsing message with Gemini: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="ai_parser", exception_type=type(e).__name__).inc()
        return {"intent": "unknown", "error": str(e)}

if __name__ == "__main__":
    # Test cases
    print(parse_user_message("buy food - $10 - Jun 9"))
    print(parse_user_message("total expense"))
    print(parse_user_message("spent 15 bucks on coffee today"))
    print(parse_user_message("tuna - $10 - June 1\ncheese - $5 - June 2\npaper towel - $5 - Jun 7\nelectricity - $100 - June 8"))
