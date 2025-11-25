import os
import json
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials


# ============================================================
# LOAD ENV VARIABLES
# ============================================================
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


# ============================================================
# GOOGLE SHEETS CONFIG (Render safe)
# ============================================================
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.loads(creds_json)

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        creds_dict, scope
    )

    client = gspread.authorize(creds)
    sheet = client.open("google sheet leadbot").sheet1   # your sheet name
    return sheet


# ============================================================
# STATES
# ============================================================
ASK_NAME, ASK_PHONE, ASK_BRANCH, ASK_SERVICE = range(4)


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Let's get your details.\n\nWhat's your *full name*?",
        parse_mode="Markdown",
    )
    return ASK_NAME


# ============================================================
# NAME
# ============================================================
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "Great! Now send me your *phone number*:",
        parse_mode="Markdown",
    )
    return ASK_PHONE


# ============================================================
# PHONE
# ============================================================
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()

    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text(
            "❌ Invalid phone number. Please enter a 10-digit number."
        )
        return ASK_PHONE

    context.user_data["phone"] = phone

    keyboard = [
        [InlineKeyboardButton("Main Branch", callback_data="Main Branch")],
        [InlineKeyboardButton("Branch 2", callback_data="Branch 2")],
        [InlineKeyboardButton("Branch 3", callback_data="Branch 3")],
    ]
    await update.message.reply_text(
        "Which branch are you interested in?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_BRANCH


# ============================================================
# BRANCH PICKED
# ============================================================
async def branch_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["branch"] = query.data

    services = [
        [InlineKeyboardButton("Gym Trial", callback_data="Gym Trial")],
        [InlineKeyboardButton("Personal Training", callback_data="Personal Training")],
        [InlineKeyboardButton("Diet Plan", callback_data="Diet Plan")],
        [InlineKeyboardButton("Transformation Program", callback_data="Transformation Program")],
    ]

    await query.edit_message_text(
        "Select the service you need:",
        reply_markup=InlineKeyboardMarkup(services),
    )
    return ASK_SERVICE


# ============================================================
# SERVICE PICKED → SAVE + NOTIFY ADMIN
# ============================================================
async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["service"] = query.data

    # save to sheet
    sheet = get_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    name = context.user_data["name"]
    phone = context.user_data["phone"]
    branch = context.user_data["branch"]
    service = context.user_data["service"]
    user_id = query.from_user.id

    sheet.append_row([
        timestamp, name, phone, service, branch, user_id
    ])

    # tell user
    await query.edit_message_text(
        "🎉 *Thanks!* Your details were submitted successfully.\n\n"
        "Someone from the team will contact you soon.",
        parse_mode="Markdown",
    )

    # notify admin
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                parse_mode="Markdown",
                text=(
                    f"📢 *New Lead*\n"
                    f"Name: {name}\n"
                    f"Phone: {phone}\n"
                    f"Branch: {branch}\n"
                    f"Service: {service}\n"
                    f"User ID: {user_id}\n"
                    f"Time: {timestamp}"
                ),
            )
        except Exception:
            pass  # avoid crashes

    return ConversationHandler.END


# ============================================================
# /leads_today
# ============================================================
async def leads_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheet = get_sheet()
    records = sheet.get_all_records()

    today = datetime.now().strftime("%Y-%m-%d")
    count = sum(1 for r in records if str(r["timestamp"]).startswith(today))

    await update.message.reply_text(
        f"📊 Leads today: *{count}*",
        parse_mode="Markdown",
    )


# ============================================================
# MAIN
# ============================================================
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

    print("🤖 Lead Bot is running on Render...")
    app.run_polling()


if __name__ == "__main__":
    main()
