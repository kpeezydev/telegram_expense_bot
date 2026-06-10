import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import uvicorn

import supabase_client
from ai_parser import parse_user_message

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# A set to keep track of users who have started the bot
active_users = set()

# Parse allowed user IDs from comma-separated env var
ALLOWED_USER_IDS = set()
raw = os.getenv("ALLOWED_USER_IDS", "")
if raw:
    ALLOWED_USER_IDS = {int(x.strip()) for x in raw.split(",") if x.strip()}

def is_authorized(update: Update) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return update.effective_user.id in ALLOWED_USER_IDS

def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        return await func(update, context)
    return wrapper

@authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    user_id = update.effective_user.id
    active_users.add(user_id)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! I'm your Expense Tracker Bot. 🧾\n\n"
             "You can send me your expenses in plain English, for example:\n"
             "- 'buy food - $10 - Jun 9'\n"
             "- 'spent 15 on coffee today'\n\n"
             "You can also send multiple expenses at once, one per line:\n"
             "- 'tuna - $10 - June 1\\ncheese - $5 - June 2'\n\n"
             "You can also ask me for the 'total expense' to see how much you've spent this month.\n\n"
             "To delete an expense, say something like 'delete expense test - $10 - Jun 9' or 'delete expense #3'.\n\n"
             "Your expenses are securely saved to the cloud, and a daily report is generated automatically."
    )

@authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="*Expense Tracker Help*\n\n"
             "1. *Adding expenses*: Just type what you spent. E.g., 'Groceries $50 yesterday'. You can also send multiple expenses at once, one per line:\n"
             "   'tuna - $10 - June 1\\ncheese - $5 - June 2'\n"
             "2. *Checking total*: Type 'total expense' or 'how much did I spend this month?'.\n"
             "3. *Listing expenses*: Ask 'show my expenses this month' or 'list from June 1 to June 10'.\n"
             "4. *Deleting expenses*: Say 'delete expense test - $10 - Jun 9' or 'delete expense #3'.\n"
             "5. *Reports*: A daily report is automatically generated and uploaded.",
        parse_mode='Markdown'
    )

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all incoming text messages."""
    user_id = update.effective_user.id
    text = update.message.text

    # Parse the message using Gemini
    parsed_data = parse_user_message(text)
    
    intent = parsed_data.get('intent')
    
    if intent == 'add_expenses':
        expenses = parsed_data.get('data', {}).get('expenses', [])

        if not expenses:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I couldn't find any expenses in your message. Could you rephrase?"
            )
            return

        valid = []
        invalid = []
        for exp in expenses:
            desc = exp.get('description', 'Unknown')
            amt = exp.get('amount')
            date_str = exp.get('date')
            if amt is not None and date_str:
                valid.append(exp)
            else:
                invalid.append(exp)

        inserted = []
        failed = []

        if valid:
            try:
                supabase_client.add_expenses_batch(user_id, valid)
                inserted = valid
            except Exception as e:
                logger.warning(f"Batch insert failed, falling back to one-by-one: {e}")
                for exp in valid:
                    try:
                        supabase_client.add_expense(
                            user_id,
                            exp['description'],
                            exp['amount'],
                            exp['date']
                        )
                        inserted.append(exp)
                    except Exception as e2:
                        logger.error(f"Error inserting expense: {e2}")
                        failed.append(exp)

        invalid.extend(failed)

        parts = []
        if inserted:
            lines = [f"✅ Added {len(inserted)} expense(s):"]
            for exp in inserted:
                lines.append(f"  • {exp['description']} — ${exp['amount']:.2f} — {exp['date']}")
            parts.append("\n".join(lines))
        if invalid:
            lines = [f"⚠️ Could not add {len(invalid)} expense(s):"]
            for exp in invalid:
                desc = exp.get('description', 'Unknown')
                amt = exp.get('amount')
                date_str = exp.get('date')
                missing = []
                if amt is None:
                    missing.append("amount")
                if not date_str:
                    missing.append("date")
                lines.append(f"  • {desc} (missing: {', '.join(missing)})")
            parts.append("\n".join(lines))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\n\n".join(parts)
        )

    elif intent == 'list_expenses':
        data = parsed_data.get('data', {})
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not start_date or not end_date:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Could you specify a timeframe? For example: 'show my expenses this month' or 'list expenses from June 1 to June 15'."
            )
            return

        # Swap if dates are reversed
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        try:
            expenses = supabase_client.get_expenses_in_range(user_id, start_date, end_date)

            if not expenses:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"No expenses found from {start_date} to {end_date}."
                )
                return

            lines = [f"📋 Expenses from {start_date} to {end_date}:"]
            total = 0.0
            for exp in expenses:
                eid = exp.get('id', '')
                d = exp.get('date', '')
                desc = exp.get('description', '')
                amt = exp.get('amount', 0)
                total += amt
                lines.append(f"• #{eid}  {d}  {desc}  ${amt:.2f}")
            lines.append(f"\n**Total: ${total:.2f}**")

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\n".join(lines),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error listing expenses: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, there was an error retrieving your expenses."
            )

    elif intent == 'get_total':
        today = datetime.now()
        try:
            total = supabase_client.get_total_expenses_for_month(user_id, today.year, today.month)
            month_name = today.strftime('%B')
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📊 Your total expense for {month_name} is: *${total:.2f}*",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error getting total: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, there was an error calculating your total."
            )

    elif intent == 'delete_expense':
        data = parsed_data.get('data', {})
        expense_id = data.get('id')

        try:
            if expense_id is not None:
                # Delete by ID
                deleted = supabase_client.delete_expense_by_id(user_id, expense_id)
                if deleted:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"🗑 Deleted expense #{expense_id}."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"No expense found with ID {expense_id}."
                    )
            else:
                description = data.get('description')
                amount = data.get('amount')
                date_str = data.get('date')

                if not description and amount is None and not date_str:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Could you be more specific? Tell me the description, amount, or date of the expense you'd like to delete."
                    )
                    return

                matches = supabase_client.find_expenses_by_match(
                    user_id, description=description, amount=amount, expense_date=date_str
                )

                if len(matches) == 0:
                    parts = []
                    if description:
                        parts.append(f"'{description}'")
                    if amount is not None:
                        parts.append(f"${amount:.2f}")
                    if date_str:
                        parts.append(date_str)
                    criteria = " - ".join(parts)
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"No expense found matching {criteria}."
                    )

                elif len(matches) == 1:
                    exp = matches[0]
                    eid = exp.get('id')
                    supabase_client.delete_expense(eid)
                    desc = exp.get('description', '')
                    amt = exp.get('amount', 0)
                    dt = exp.get('date', '')
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"🗑 Deleted expense: {desc} - ${amt:.2f} - {dt}"
                    )

                else:
                    lines = ["Multiple expenses match. Which one would you like to delete? Reply with the ID number (e.g., 'delete expense #3'):"]
                    for exp in matches:
                        eid = exp.get('id')
                        d = exp.get('date', '')
                        desc = exp.get('description', '')
                        amt = exp.get('amount', 0)
                        lines.append(f"  #{eid}  {d}  {desc}  ${amt:.2f}")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="\n".join(lines)
                    )
        except Exception as e:
            logger.error(f"Error deleting expense: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, there was an error deleting this expense."
            )

    else:
        # Unknown intent
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm not sure what you mean. You can tell me an expense (e.g., 'spent 10 on food'), ask for 'total expense', list expenses by timeframe (e.g., 'show my expenses this month'), or delete an expense (e.g., 'delete expense test - $10 - Jun 9')."
        )

# Build application at module level (shared by polling and webhook modes)
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build() if TELEGRAM_BOT_TOKEN else None

if application:
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# FastAPI app for webhook mode (Cloud Run)
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if application:
        await application.initialize()
        await application.start()
        logger.info("Bot application started (webhook mode)")
    yield
    if application:
        await application.stop()
        await application.shutdown()
        logger.info("Bot application stopped")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if SECRET_TOKEN and secret != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env file.")
        exit(1)

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        port = int(os.getenv("PORT", 8080))
        logger.info(f"Starting webhook server on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        logger.info("Bot is starting (polling mode)...")
        application.run_polling()
