import logging
import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Bot Token from environment
TOKEN = os.getenv("BOT_TOKEN")

# Admin Telegram username
ADMIN_USERNAME = "anurag_1938"

# PHP API endpoint
API_ENDPOINT = "https://go.trustearn.in/bot/get_movie.php"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Send me a movie name to get its link and details.")

# Handle Movie Queries
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "unknown"

    # Call your PHP API to fetch movie
    try:
        response = requests.get(API_ENDPOINT, params={"name": user_query})
        data = response.json()
    except Exception as e:
        await update.message.reply_text("⚠️ Failed to connect to server. Please try again later.")
        print("API error:", e)
        return

   if data.get("status") == "found":
        keyboard = []

        for quality in ['360p', '480p', '720p', '1080p']:
            link = data.get(f"link_{quality}")
            if link:
                keyboard.append(
                    InlineKeyboardButton(text=f"{quality} Download", url=link)
                )

        reply_markup = InlineKeyboardMarkup.from_column(keyboard)

        message = f"""🎬 *{data['movie_name']}*

📝 {data['movie_paragraph']}

⬇️ Select Quality Below:"""
        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)
        notify_admin = f"✅ User @{username} searched: *{user_query}* - Found match with qualities"

    else:
        await update.message.reply_text("❌ Movie not found. Please check again after 24 hours.")
        notify_admin = f"❌ User @{username} searched: *{user_query}* - Not found"

    # Notify Admin
    try:
        await context.bot.send_message(chat_id=f"@{ADMIN_USERNAME}", text=notify_admin, parse_mode="Markdown")
    except Exception as e:
        print("Failed to notify admin:", e)

# Main
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🤖 Bot is running...")
    app.run_polling()
