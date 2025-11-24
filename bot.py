import os
from dotenv import load_dotenv
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials


# -----------------------------------
# LOAD ENV VARIABLES
# -----------------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # new


# -----------------------------------
# GOOGLE SHEETS SETUP
# -----------------------------------
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials/google-creds.json", scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("google sheet leadbot").sheet1   # your file name
    return sheet


# -----------------------------------
# CONVERSATION STATES
# -----------------------------------
ASK_NAME, ASK_PHONE, ASK_BRANCH, ASK_SERVICE = range(4)


# -----------------------------------
# /start
# -----------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Let's get your details.\n\nWhat's your *full name*?",
        parse_mode="Markdown",
    )
    return ASK_NAME


# -----------------------------------
# NAME
# -----------------------------------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Great! Now send me your *phone number*:", parse_mode="Markdown")
    return ASK_PHONE


# -----------------------------------
# PHONE
# -----------------------------------
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()

    if not phone.isdigit() or len(phone) < 10 or len(phone) > 10:
        await update.message.reply_text("❌ Invalid phone number. Please enter digits only.")
        return ASK_PHONE

    context.user_data["phone"] = phone

    # ask for branch (multi-location support)
    keyboard = [
        [InlineKeyboardButton("Main Branch", callback_data="Main Branch")],
        [InlineKeyboardButton("Branch 2", callback_data="Branch 2")],
        [InlineKeyboardButton("Branch 3", callback_data="Branch 3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Which branch are you interested in?", reply_markup=reply_markup)
    return ASK_BRANCH


# -----------------------------------
# BRANCH SELECTED
# -----------------------------------
async def branch_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    branch = query.data
    context.user_data["branch"] = branch

    # now ask for service
    keyboard = [
        [InlineKeyboardButton("Gym Trial", callback_data="Gym Trial")],
        [InlineKeyboardButton("Personal Training", callback_data="Personal Training")],
        [InlineKeyboardButton("Diet Plan", callback_data="Diet Plan")],
        [InlineKeyboardButton("Transformation Program", callback_data="Transformation Program")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Select the service you need:", reply_markup=reply_markup)
    return ASK_SERVICE


# -----------------------------------
# SERVICE SELECTED (SAVE + NOTIFY ADMIN)
# -----------------------------------
async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    service = query.data
    context.user_data["service"] = service

    # SAVE TO GOOGLE SHEETS
    sheet = get_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    name = context.user_data["name"]
    phone = context.user_data["phone"]
    branch = context.user_data["branch"]
    user_id = query.from_user.id

    # make sure your header row in sheet is:
    # timestamp | name | phone | service | branch | userid
    sheet.append_row([
        timestamp,
        name,
        phone,
        service,
        branch,
        user_id,
    ])

    # notify user
    await query.edit_message_text(
        "🎉 *Thanks!* Your details were submitted successfully.\n\n"
        "Someone from the team will contact you soon.",
        parse_mode="Markdown",
    )

    # notify admin (you or gym owner)
    if ADMIN_CHAT_ID:
        text = (
            f"📢 *New Lead*\n"
            f"Name: {name}\n"
            f"Phone: {phone}\n"
            f"Branch: {branch}\n"
            f"Service: {service}\n"
            f"User ID: {user_id}\n"
            f"Time: {timestamp}"
        )
        try:
            await context.bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=text, parse_mode="Markdown")
        except Exception:
            # don’t crash the bot if admin id invalid
            pass

    return ConversationHandler.END


# -----------------------------------
# ADMIN COMMAND: /leads_today
# -----------------------------------
async def leads_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet = get_sheet()
    # header row: timestamp | name | phone | service | branch | userid
    records = sheet.get_all_records()

    today = datetime.now().strftime("%Y-%m-%d")
    count = sum(1 for r in records if str(r["timestamp"]).startswith(today))

    await update.message.reply_text(f"📊 Leads today: *{count}*", parse_mode="Markdown")


# -----------------------------------
# MAIN
# -----------------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ASK_BRANCH: [CallbackQueryHandler(branch_selected)],
            ASK_SERVICE: [CallbackQueryHandler(service_selected)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("leads_today", leads_today))

    print("🤖 Lead Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
