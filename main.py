import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

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
             "You can also ask me for the 'total expense' to see how much you've spent this month.\n\n"
             "Your expenses are securely saved to the cloud, and a daily report is generated automatically."
    )

@authorized
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="*Expense Tracker Help*\n\n"
             "1. *Adding an expense*: Just type what you spent. E.g., 'Groceries $50 yesterday'.\n"
             "2. *Checking total*: Type 'total expense' or 'how much did I spend this month?'.\n"
             "3. *Listing expenses*: Ask 'show my expenses this month' or 'list from June 1 to June 10'.\n"
             "4. *Reports*: A daily report is automatically generated and uploaded.",
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
    
    if intent == 'add_expense':
        data = parsed_data.get('data', {})
        description = data.get('description', 'Unknown expense')
        amount = data.get('amount')
        date_str = data.get('date') # Expected YYYY-MM-DD
        
        if amount is None or not date_str:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="I couldn't quite understand the amount or date. Could you rephrase?"
            )
            return

        try:
            # Save to database
            supabase_client.add_expense(user_id, description, amount, date_str)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Added expense:\nDescription: {description}\nAmount: ${amount}\nDate: {date_str}"
            )
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, there was an error saving your expense."
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
                d = exp.get('date', '')
                desc = exp.get('description', '')
                amt = exp.get('amount', 0)
                total += amt
                lines.append(f"• {d}  {desc}  ${amt:.2f}")
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

    else:
        # Unknown intent
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm not sure what you mean. You can tell me an expense (e.g., 'spent 10 on food'), ask for 'total expense', or list expenses by timeframe (e.g., 'show my expenses this month')."
        )

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env file.")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Bot is starting...")
    # This call blocks until the bot is stopped
    application.run_polling()
