from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import requests

# ----------------- CONFIG -----------------
TOKEN = "8302301164:AAF6uaZT8NojETMWWILcBH0R97-3d1IxiVI"  # Replace with your bot token

# ----------------- URL SHORTENER -----------------
def shorten_url(url, alias=None):
    try:
        if alias:
            api_url = f"https://is.gd/create.php?format=simple&url={url}&shorturl={alias}"
        else:
            api_url = f"https://is.gd/create.php?format=simple&url={url}"
        response = requests.get(api_url, timeout=10)
        return response.text
    except:
        return "❌ Error shortening URL"

# ----------------- SIMPLE URL VALIDATION -----------------
def is_valid_url(url):
    return "." in url  # basic check

# ----------------- COMMANDS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Welcome to URL Shortener Bot\n\n"
        "Send a link and see magic 🪄"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ This bot can take long URLs and compress them into small short links.\n"
        "It is fully based on the is.gd API.\n\n"
        "1️⃣ Send a URL that you want to shorten\n\n"
        "2️⃣ The bot will reply with the shortened link\n\n"
        "3️⃣ Custom alias:\n"
        "   Type your 'long link' + space + 'custom text'\n"
        "   Example: https://www.youtube.com ytxyz\n"
        "   Result: https://is.gd/ytxyz\n\n"
        "🆕 Multi-link feature:\n"
        "   Send multiple links using new lines.\n"
        "   The bot will process them one by one."
    )

# ----------------- MESSAGE HANDLER -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    total = len(lines)
    processed = 0

    # Progress message
    progress_msg = await update.message.reply_text(f"⏳ Processing 0/{total}...")

    for line in lines:
        parts = line.split()
        url = parts[0]

        if not url.startswith("http"):
            url = "https://" + url

        if not is_valid_url(url):
            await update.message.reply_text(f"❌ Invalid URL:\n{url}")
            continue

        alias = parts[1] if len(parts) > 1 else None

        short_link = shorten_url(url, alias)
        await update.message.reply_text(f"🔗 {short_link}")

        processed += 1
        try:
            await progress_msg.edit_text(f"⏳ Processing {processed}/{total}...")
        except:
            pass

    try:
        await progress_msg.edit_text(f"✅ Completed {processed}/{total} link(s).")
    except:
        pass

# ----------------- BOT SETUP -----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 Bot running...")
app.run_polling()
