import logging
import mysql.connector
import os
from difflib import get_close_matches
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Bot Token from environment
TOKEN = os.getenv("BOT_TOKEN")

# Database Connection using environment variables
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )

# Admin Telegram username
ADMIN_USERNAME = "anurag_1938"

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Welcome! Send me a movie name to get its link and details.")

# Handle Movie Queries
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text.strip()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "unknown"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Exact match
    cursor.execute("SELECT * FROM movies WHERE movie_name = %s", (user_query,))
    movie = cursor.fetchone()

    if movie:
        cursor.execute("INSERT INTO queries (user_id, username, query_text, matched_movie, is_found) VALUES (%s, %s, %s, %s, 1)",
                       (user_id, username, user_query, movie['movie_name']))
        conn.commit()

        reply = f"""🎬 *{movie['movie_name']}*

📎 Link: {movie['movie_link']}
📝 Description: {movie['movie_paragraph']}"""
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        cursor.execute("SELECT movie_name FROM movies")
        all_movies = [row['movie_name'] for row in cursor.fetchall()]
        suggestions = get_close_matches(user_query, all_movies, n=3, cutoff=0.5)

        matched_movie = suggestions[0] if suggestions else None
        if matched_movie:
            cursor.execute("SELECT * FROM movies WHERE movie_name = %s", (matched_movie,))
            suggested = cursor.fetchone()

            if suggested and not suggested['movie_link']:
                msg = f"🔍 Found similar movie: *{matched_movie}*
❌ But the link is not uploaded yet.
⏳ Check again in 24 hours."
                await update.message.reply_text(msg, parse_mode="Markdown")

                notify_admin = f"⚠️ User @{username} searched for *{user_query}*.
Suggested: *{matched_movie}*, but link is missing."
            else:
                msg = f"🔍 Found similar movie: *{matched_movie}*
📎 Link: {suggested['movie_link']}
📝 {suggested['movie_paragraph']}"
                await update.message.reply_text(msg, parse_mode="Markdown")
                notify_admin = f"✅ User @{username} searched: *{user_query}*, suggested: *{matched_movie}*"

            cursor.execute("INSERT INTO queries (user_id, username, query_text, matched_movie, is_found) VALUES (%s, %s, %s, %s, 0)",
                           (user_id, username, user_query, matched_movie))
            conn.commit()
        else:
            await update.message.reply_text("❌ Movie not found. Please check again after 24 hours.")
            notify_admin = f"❌ User @{username} searched: *{user_query}* (no match)"

            cursor.execute("INSERT INTO queries (user_id, username, query_text, matched_movie, is_found) VALUES (%s, %s, %s, NULL, 0)",
                           (user_id, username, user_query))
            conn.commit()

        # Notify Admin
        try:
            await context.bot.send_message(chat_id=f"@{ADMIN_USERNAME}", text=notify_admin, parse_mode="Markdown")
        except Exception as e:
            print("Failed to notify admin:", e)

    cursor.close()
    conn.close()

# Main
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🤖 Bot is running...")
    app.run_polling()
