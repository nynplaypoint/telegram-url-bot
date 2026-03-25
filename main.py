from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import requests

def shorten_url(url, alias=None):
    if alias:
        api_url = f"https://is.gd/create.php?format=simple&url={url}&shorturl={alias}"
    else:
        api_url = f"https://is.gd/create.php?format=simple&url={url}"
    
    response = requests.get(api_url)
    return response.text

async def handle_message(update: Update, context):
    text = update.message.text.strip()

    parts = text.split()

    if len(parts) == 0:
        return

    url = parts[0]

    # Auto-fix URL (add https if missing)
    if not url.startswith("http"):
        url = "https://" + url

    alias = None
    if len(parts) > 1:
        alias = parts[1]

    short_link = shorten_url(url, alias)

    if "Error" in short_link:
        await update.message.reply_text(f"❌ Error:\n{short_link}")
    else:
        await update.message.reply_text(f"🔗 Short Link:\n{short_link}")

app = ApplicationBuilder().token("8302301164:AAF6uaZT8NojETMWWILcBH0R97-3d1IxiVI").build()
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()