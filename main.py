from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
import requests
import asyncio
import re

# ----------------- URL Validator -----------------
def is_valid_url(url):
    regex = re.compile(
        r'^(https?:\/\/)?'  # http:// or https://
        r'([\w\-]+\.)+[\w\-]+'  # domain
        r'([\/\w\-\.\?\=\&\#]*)*\/?$'  # path
    )
    return re.match(regex, url)

# ----------------- URL Shortener -----------------
def shorten_url(url, alias=None):
    if alias:
        api_url = f"https://is.gd/create.php?format=simple&url={url}&shorturl={alias}"
    else:
        api_url = f"https://is.gd/create.php?format=simple&url={url}"
    
    response = requests.get(api_url)
    return response.text

# ----------------- Commands -----------------
async def start(update: Update, context):
    await update.message.reply_text(
        "✨ This is a URL shortener based on the is.gd API.\n\n"
        "Send a link and see magic 🪄"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "ℹ️ Features:\n\n"
        "• Shorten any URL\n"
        "• Custom alias support\n"
        "• Multi-link (newline supported)\n"
        "• Button UI for easy access\n\n"
        "📌 Usage:\n"
        "1. Send a URL\n"
        "2. Or multiple URLs (line by line)\n"
        "3. Custom alias:\n"
        "   https://example.com myalias\n"
    )

# ----------------- Message Handler -----------------
async def handle_message(update: Update, context):
    text = update.message.text.strip()
    lines = text.split("\n")

    total = len([l for l in lines if l.strip()])
    count = 0

    # Send initial progress message
    progress_msg = await update.message.reply_text(f"⏳ Processing 0/{total}...")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        url = parts[0]

        # Auto-fix URL
        if not url.startswith("http"):
            url = "https://" + url

        # Validate URL
        if not is_valid_url(url):
            await update.message.reply_text(f"❌ Invalid URL:\n{url}")
            continue

        alias = None
        if len(parts) > 1:
            alias = parts[1]

        short_link = shorten_url(url, alias)

        if "Error" in short_link:
            await update.message.reply_text(f"❌ Error:\n{short_link}")
        else:
            # Button UI
            keyboard = [
                [InlineKeyboardButton("🔗 Open Link", url=short_link)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✅ Shortened:\n{short_link}",
                reply_markup=reply_markup
            )

        count += 1

        # Update progress
        await progress_msg.edit_text(f"⏳ Processing {count}/{total}...")

        await asyncio.sleep(1)

    await progress_msg.edit_text(f"✅ Done! Processed {count} link(s).")

# ----------------- Bot Setup -----------------
app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
