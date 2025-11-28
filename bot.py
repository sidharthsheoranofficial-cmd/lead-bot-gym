import os
import json
from datetime import datetime

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
# GOOGLE SHEETS CONFIG (Render + Webhook safe)
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
    sheet = client.open("google sheet leadbot").sheet1
    return sheet


# ============================================================
# NEW STATES
# ============================================================
(
    ASK_NAME,
    ASK_PHONE,
    ASK_GOAL,
    ASK_EXPERIENCE,
    ASK_TIME,
    ASK_INTEREST,
    ASK_INJURY,
    ASK_BRANCH,
    ASK_SERVICE,
) = range(9)


# ============================================================
# /start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! 👋 Thanks for reaching out to XYZ Gym. I'd love to help you get started.\n\n"
        "Before I guide you further, let’s begin with your *full name* 🙂",
        parse_mode="Markdown",
    )
    return ASK_NAME


# ============================================================
# NAME
# ============================================================
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()

    await update.message.reply_text(
        "Great! Please enter your *phone number*.\nWe need it to contact you & reach out to you.",
        parse_mode="Markdown",
    )
    return ASK_PHONE


# ============================================================
# PHONE
# ============================================================
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()

    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid phone number. Enter 10 digits.")
        return ASK_PHONE

    context.user_data["phone"] = phone

    # Q3 — GOAL BUTTONS
    keyboard = [
        [InlineKeyboardButton("Lose Weight", callback_data="Lose Weight")],
        [InlineKeyboardButton("Build Muscle", callback_data="Build Muscle")],
        [InlineKeyboardButton("Get Fitter", callback_data="Get Fitter")],
        [InlineKeyboardButton("Improve Stamina", callback_data="Improve Stamina")],
        [InlineKeyboardButton("General Fitness", callback_data="General Fitness")],
    ]

    await update.message.reply_text(
        "Awesome! What is your *current fitness goal*?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_GOAL


# ============================================================
# GOAL SELECTED
# ============================================================
async def goal_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["goal"] = query.data

    # Q4 — EXPERIENCE BUTTONS
    keyboard = [
        [InlineKeyboardButton("Beginner", callback_data="Beginner")],
        [InlineKeyboardButton("Intermediate", callback_data="Intermediate")],
        [InlineKeyboardButton("Advanced", callback_data="Advanced")],
    ]

    await query.edit_message_text(
        "Great! How would you describe your *fitness experience*?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_EXPERIENCE


# ============================================================
# EXPERIENCE SELECTED
# ============================================================
async def experience_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["experience"] = query.data

    # Q5 — TIME BUTTONS
    keyboard = [
        [InlineKeyboardButton("Morning", callback_data="Morning")],
        [InlineKeyboardButton("Afternoon", callback_data="Afternoon")],
        [InlineKeyboardButton("Evening", callback_data="Evening")],
    ]

    await query.edit_message_text(
        "Nice! What time do you *prefer working out*?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_TIME


# ============================================================
# TIME SELECTED
# ============================================================
async def time_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["time"] = query.data

    # Q6 — TYPE OF INTEREST
    keyboard = [
        [InlineKeyboardButton("Free Trial", callback_data="Free Trial")],
        [InlineKeyboardButton("Membership Info", callback_data="Membership Info")],
        [InlineKeyboardButton("Personal Training", callback_data="Personal Training")],
    ]

    await query.edit_message_text(
        "Perfect! What are you looking for?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_INTEREST


# ============================================================
# INTEREST SELECTED
# ============================================================
async def interest_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["interest"] = query.data

    await query.edit_message_text(
        "Got it! Last question — do you have any *injuries or medical conditions*?\n\n"
        "_If none, type: No_",
        parse_mode="Markdown",
    )
    return ASK_INJURY


# ============================================================
# INJURY
# ============================================================
async def injury_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["injury"] = update.message.text.strip()

    # Q8 — BRANCH BUTTON
    keyboard = [
        [InlineKeyboardButton("Main Branch", callback_data="Main Branch")],
        [InlineKeyboardButton("Branch 2", callback_data="Branch 2")],
        [InlineKeyboardButton("Branch 3", callback_data="Branch 3")],
    ]

    await update.message.reply_text(
        "Which *branch* are you interested in?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_BRANCH


# ============================================================
# BRANCH SELECTED
# ============================================================
async def branch_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["branch"] = query.data

    keyboard = [
        [InlineKeyboardButton("Gym Trial", callback_data="Gym Trial")],
        [InlineKeyboardButton("Personal Training", callback_data="Personal Training")],
        [InlineKeyboardButton("Diet Plan", callback_data="Diet Plan")],
        [InlineKeyboardButton("Transformation Program", callback_data="Transformation Program")],
    ]

    await query.edit_message_text(
        "Select the service you need:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_SERVICE


# ============================================================
# SERVICE SELECTED → SAVE TO SHEET
# ============================================================
async def service_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["service"] = query.data

    sheet = get_sheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Extract all fields
    name = context.user_data["name"]
    phone = context.user_data["phone"]
    goal = context.user_data["goal"]
    experience = context.user_data["experience"]
    time_pref = context.user_data["time"]
    interest = context.user_data["interest"]
    injury = context.user_data["injury"]
    branch = context.user_data["branch"]
    service = context.user_data["service"]
    user_id = query.from_user.id

    # SAVE ALL 10 FIELDS
    sheet.append_row([
        timestamp, name, phone, goal, experience, time_pref,
        interest, injury, branch, service, user_id
    ])

    await query.edit_message_text(
        "🎉 *Thanks!* Your details were submitted successfully.\n\n"
        "Someone from the team will contact you soon.",
        parse_mode="Markdown",
    )

    # ADMIN ALERT
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_CHAT_ID),
                text=(
                    f"📢 *New Lead*\n"
                    f"Name: {name}\n"
                    f"Phone: {phone}\n"
                    f"Goal: {goal}\n"
                    f"Experience: {experience}\n"
                    f"Time: {time_pref}\n"
                    f"Interest: {interest}\n"
                    f"Injury: {injury}\n"
                    f"Branch: {branch}\n"
                    f"Service: {service}\n"
                    f"User ID: {user_id}\n"
                    f"Time: {timestamp}"
                ),
                parse_mode="Markdown",
            )
        except:
            pass

    return ConversationHandler.END


# ============================================================
# ADMIN COMMAND: /leads_today
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
# BUILD BOT APPLICATION
# ============================================================
def build_bot_app():
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],

            ASK_GOAL: [CallbackQueryHandler(goal_selected)],
            ASK_EXPERIENCE: [CallbackQueryHandler(experience_selected)],
            ASK_TIME: [CallbackQueryHandler(time_selected)],
            ASK_INTEREST: [CallbackQueryHandler(interest_selected)],
            ASK_INJURY: [MessageHandler(filters.TEXT & ~filters.COMMAND, injury_received)],

            ASK_BRANCH: [CallbackQueryHandler(branch_selected)],
            ASK_SERVICE: [CallbackQueryHandler(service_selected)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("leads_today", leads_today))

    return app
