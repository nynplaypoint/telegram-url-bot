import logging
import os
import requests
import qrcode
import io
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ── CONFIG ─────────────────────────────────────────────────────────────────────
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_SERVICE = os.getenv("DEFAULT_SERVICE", "isgd")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found! Check your .env file.")
# ───────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SERVICES = {
    "isgd":    {"name": "is.gd",   "emoji": "🟢"},
    "vgd":     {"name": "v.gd",    "emoji": "🔵"},
    "tinyurl": {"name": "TinyURL", "emoji": "🟠"},
}
SERVICE_ORDER = ["isgd", "vgd", "tinyurl"]
user_service: dict[int, str] = {}


def get_service(user_id: int) -> str:
    return user_service.get(user_id, DEFAULT_SERVICE)


def get_label(key: str) -> str:
    return SERVICES[key]["emoji"] + " " + SERVICES[key]["name"]


# HTML helpers
def b(text: str) -> str:
    return "<b>" + text + "</b>"

def code(text: str) -> str:
    return "<code>" + text + "</code>"

def i(text: str) -> str:
    return "<i>" + text + "</i>"


# ── URL HELPERS ────────────────────────────────────────────────────────────────

def looks_like_url(text: str) -> bool:
    t = text.strip()
    if t.startswith("http://") or t.startswith("https://"):
        return True
    if "." in t and " " not in t and len(t) > 3:
        parts = t.split(".")
        if all(p for p in parts):
            return True
    return False


def add_https(url: str) -> str:
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


def preview(url: str, limit: int = 55) -> str:
    return url[:limit] + ("..." if len(url) > limit else "")


def friendly(raw: str) -> str:
    if raw == "alias taken":
        return "Alias already taken"
    if raw == "timeout":
        return "Request timed out"
    return "Service error"


# ── SHORTENING ────────────────────────────────────────────────────────────────

def do_isgd(url: str, alias: str, domain: str) -> tuple[bool, str]:
    base = "https://is.gd/create.php" if domain == "isgd" else "https://v.gd/create.php"
    params = {"format": "simple", "url": url}
    if alias:
        params["shorturl"] = alias
    try:
        r = requests.get(base, params=params, timeout=10)
        t = r.text.strip()
        if r.status_code == 200 and t.startswith("http"):
            return True, t
        if "already in use" in t.lower():
            return False, "alias taken"
        return False, "error"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except Exception as e:
        logger.error(e)
        return False, "error"


def do_tinyurl(url: str, alias: str) -> tuple[bool, str]:
    params = {"url": url}
    if alias:
        params["alias"] = alias
    try:
        r = requests.get("https://tinyurl.com/api-create.php", params=params, timeout=10)
        t = r.text.strip()
        if r.status_code == 200 and t.startswith("http"):
            return True, t
        if r.status_code == 422:
            return False, "alias taken"
        return False, "error"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except Exception as e:
        logger.error(e)
        return False, "error"


def shorten(url: str, svc: str, alias: str = "") -> tuple[bool, str]:
    url = add_https(url)
    alias = alias.strip()
    if svc in ("isgd", "vgd"):
        return do_isgd(url, alias, svc)
    return do_tinyurl(url, alias)


# ── PARSE LINES ───────────────────────────────────────────────────────────────

def parse_lines(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        url = parts[0]
        alias = parts[1] if len(parts) >= 2 else ""
        if looks_like_url(url):
            out.append((url, alias))
    return out


# ── QR CODE ───────────────────────────────────────────────────────────────────

def make_qr(url: str) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    buf.name = "qr.png"
    return buf


# ── KEYBOARD ──────────────────────────────────────────────────────────────────

def kb(short_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Open", url=short_url),
            InlineKeyboardButton("📷 QR Code", callback_data="qr:" + short_url),
        ],
        [InlineKeyboardButton("📋 Share", switch_inline_query=short_url)],
    ])


# ── HANDLERS ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    svc = get_service(uid)
    await update.message.reply_text(
        b("✂️ URL Shortener Bot") + "\n\n"
        "Active: " + get_label(svc) + "\n\n"
        + b("How to use:") + "\n"
        "Send one or more URLs, one per line.\n"
        "Examples:\n"
        + code("facebook.com") + "\n"
        + code("https://example.com myalias") + "\n\n"
        + b("Switch service:") + "\n"
        + code("/switch") + " — cycle to next\n"
        + code("/switch isgd") + " — `is.gd` (default)\n"
        + code("/switch vgd") + " — v.gd\n"
        + code("/switch tinyurl") + " — TinyURL\n\n"
        + code("/service") + " — show active service\n"
        + code("/help") + " — show this message\n\n"
        "Send a URL to get started! 👇",
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def service_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    svc = get_service(uid)
    lines = []
    for key in SERVICE_ORDER:
        mark = " ◀ active" if key == svc else ""
        lines.append(get_label(key) + mark)
    await update.message.reply_text(
        b("Services:") + "\n\n" + "\n".join(lines) + "\n\nUse /switch to change.",
        parse_mode="HTML"
    )


async def switch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    current = get_service(uid)
    args = context.args

    if not args:
        idx = SERVICE_ORDER.index(current)
        new_svc = SERVICE_ORDER[(idx + 1) % len(SERVICE_ORDER)]
    else:
        arg = args[0].lower().strip().replace(".", "").replace("-", "")
        mapping = {
            "isgd": "isgd", "isg": "isgd", "is": "isgd",
            "vgd": "vgd", "vg": "vgd",
            "tinyurl": "tinyurl", "tiny": "tinyurl", "tu": "tinyurl",
        }
        new_svc = mapping.get(arg)
        if not new_svc:
            await update.message.reply_text(
                "❓ Unknown service. Options:\n\n"
                + code("/switch isgd") + " — is.gd\n"
                + code("/switch vgd") + " — v.gd\n"
                + code("/switch tinyurl") + " — TinyURL\n"
                + code("/switch") + " — cycle through all",
                parse_mode="HTML"
            )
            return

    user_service[uid] = new_svc
    await update.message.reply_text(
        "✅ Switched to " + get_label(new_svc) + "\n"
        "Links will now shorten with " + b(SERVICES[new_svc]["name"]) + ".",
        parse_mode="HTML"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    svc = get_service(uid)
    sname = SERVICES[svc]["name"]
    semoji = SERVICES[svc]["emoji"]

    links = parse_lines(text)

    if not links:
        await update.message.reply_text(
            "👋 Send me a URL to shorten it.\n"
            "Active: " + get_label(svc) + "\n\n"
            "Use /help to see all commands."
        )
        return

    total = len(links)

    # Single link
    if total == 1:
        url, alias = links[0]
        norm = add_https(url)
        msg = await update.message.reply_text("✂️ Shortening with " + sname + "...")
        ok, result = shorten(url, svc, alias)
        if ok:
            await msg.edit_text(
                semoji + " " + b("Shortened with " + sname) + "\n\n"
                "🔗 " + code(result) + "\n\n"
                "📎 " + i(preview(norm)),
                parse_mode="HTML",
                reply_markup=kb(result)
            )
        else:
            await msg.edit_text(
                "❌ Failed: " + friendly(result) + "\n"
                "📎 " + preview(norm)
            )
        return

    # Multiple links
    prog = ["⏳ " + str(n + 1) + "/" + str(total) + " Waiting..." for n in range(total)]
    msg = await update.message.reply_text(
        "✂️ Shortening " + str(total) + " links with " + sname + "...\n\n"
        + "\n".join(prog)
    )

    done_results = []

    for idx, (url, alias) in enumerate(links):
        norm = add_https(url)
        prog[idx] = "⏳ " + str(idx + 1) + "/" + str(total) + " Shortening..."
        await msg.edit_text(
            "✂️ Shortening " + str(total) + " links with " + sname + "...\n\n"
            + "\n".join(prog)
        )

        ok, result = shorten(url, svc, alias)
        done_results.append((norm, ok, result))

        if ok:
            prog[idx] = "✅ " + str(idx + 1) + "/" + str(total) + " " + result
        else:
            prog[idx] = "❌ " + str(idx + 1) + "/" + str(total) + " " + friendly(result)

        await msg.edit_text(
            "✂️ Shortening " + str(total) + " links with " + sname + "...\n\n"
            + "\n".join(prog)
        )

    success_count = sum(1 for _, ok, _ in done_results if ok)
    fail_count = total - success_count

    summary = [semoji + " " + b("Done — " + str(success_count) + "/" + str(total) + " shortened") + "\n"]
    for idx, (norm, ok, result) in enumerate(done_results):
        n = str(idx + 1) + ". "
        if ok:
            summary.append(n + "✅ " + code(result) + "\n   " + i(preview(norm)))
        else:
            summary.append(n + "❌ " + friendly(result) + "\n   " + i(preview(norm)))
    if fail_count:
        summary.append("\n⚠️ " + str(fail_count) + " link(s) failed.")

    await msg.edit_text("\n".join(summary), parse_mode="HTML")

    for idx, (norm, ok, result) in enumerate(done_results):
        if ok:
            await update.message.reply_text(
                "🔗 " + b("Link " + str(idx + 1) + ":") + " " + code(result),
                parse_mode="HTML",
                reply_markup=kb(result)
            )


async def qr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Generating QR code...")
    short_url = query.data[3:]
    try:
        buf = make_qr(short_url)
        await query.message.reply_photo(
            photo=buf,
            caption="📷 QR Code for:\n" + short_url + "\n\nmore options @qrnynbot"
        )
    except Exception as e:
        logger.error(f"QR error: {e}")
        await query.message.reply_text("❌ Failed to generate QR code.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("service", service_command))
    app.add_handler(CommandHandler("switch", switch_command))
    app.add_handler(CallbackQueryHandler(qr_callback, pattern=r"^qr:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
