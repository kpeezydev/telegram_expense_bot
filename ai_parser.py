import os
import json
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

def parse_user_message(message: str) -> dict:
    """Parses a user message using the new google-genai SDK."""
    if not api_key:
        print("Warning: GEMINI_API_KEY is not set.")
        return {"intent": "unknown"}
        
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
1. Provide an expense in various formats (e.g., "name of expense - amount - date", "I spent $10 on food", "15 for coffee yesterday").
2. Ask for the total expense (e.g., "total expense", "how much did I spend this month?").

Determine the intent and extract information.

Possible intents:
- "add_expense"
- "get_total"
- "unknown"

If intent is "add_expense", provide:
- "description": A short string describing what the expense was.
- "amount": A float representing the amount spent.
- "date": A string in "YYYY-MM-DD" format. Infer the date if they use words like "today", "yesterday", or just a month/day based on the current year. If no date is provided, assume today.

If intent is "get_total", you don't need to provide description, amount, or date.
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
                            "enum": ["add_expense", "get_total", "unknown"]
                        },
                        "data": {
                            "type": "OBJECT",
                            "properties": {
                                "description": {"type": "STRING"},
                                "amount": {"type": "NUMBER"},
                                "date": {"type": "STRING"}
                            }
                        }
                    },
                    "required": ["intent"]
                }
            )
        )
        
        result_text = response.text
        result_json = json.loads(result_text)
        return result_json
        
    except Exception as e:
        print(f"Error parsing message with Gemini: {e}")
        return {"intent": "unknown", "error": str(e)}

if __name__ == "__main__":
    # Test cases
    print(parse_user_message("buy food - $10 - Jun 9"))
    print(parse_user_message("total expense"))
    print(parse_user_message("spent 15 bucks on coffee today"))
