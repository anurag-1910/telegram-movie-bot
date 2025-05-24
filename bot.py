import logging
import os
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Bot Token from environment
TOKEN = os.getenv("BOT_TOKEN")

# Admin Telegram ID
ADMIN_CHAT_ID = 1772086574  # replace with your actual ID

# API Endpoints
API_ENDPOINT = "https://go.trustearn.in/bot/get_movie.php"
LOG_ENDPOINT = "https://go.trustearn.in/bot/log_query.php"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Send me a movie name to get its link and details.")

# Handle Movie Queries
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "unknown"
    matched_movie = None
    is_found = 0

    try:
        response = requests.get(API_ENDPOINT, params={"name": user_query})
        data = response.json()
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to connect to server. Please try again later.")
        print("API error:", e)
        return

    if data.get("status") == "found":
        matched_movie = data.get("movie_name")
        is_found = 1

        keyboard = []
        for quality in ['360p', '480p', '720p', '1080p', '2k', '4k']:
            link = data.get(f"link_{quality}")
            if link:
                keyboard.append(InlineKeyboardButton(text=f"{quality.upper()} Download", url=link))

        reply_markup = InlineKeyboardMarkup.from_column(keyboard)

        caption = f"""🎬 *{matched_movie}*

📝 {data['movie_paragraph']}

⬇️ Select Quality Below:"""

        if data.get("poster"):
            await update.message.reply_photo(photo=data['poster'], caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=reply_markup)

        notify_admin = f"User @{username} searched: {user_query} — Match found"
    else:
        await update.message.reply_text("❌ Movie not found. Please check again after 24 hours.")
        notify_admin = f"User @{username} searched: {user_query} — No match found"

    # Notify Admin
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=notify_admin)  # 👈 No parse_mode
    except Exception as e:
        print("Failed to notify admin:", e)

    # Save query to database
    try:
        requests.post(LOG_ENDPOINT, json={
            "user_id": user_id,
            "username": username,
            "query_text": user_query,
            "matched_movie": matched_movie,
            "is_found": is_found
        })
    except Exception as e:
        print("Failed to log query:", e)

# Main
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🤖 Bot is running...")
    app.run_polling()
