import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
import db.client as db
from datetime import datetime

# ─── Security ───────────────────────────────────────────
async def is_admin(update: Update) -> bool:
    if update.effective_user.id != TELEGRAM_ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return False
    return True

# ─── Commands ───────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    await update.message.reply_text(
        "👋 *ESIC Monitor Admin Bot*\n\n"
        "Available commands:\n"
        "/addlink <url> <name> — Add new URL\n"
        "/removelink <url> — Remove a URL\n"
        "/listlinks — Show all monitored URLs\n"
        "/status — System status\n"
        "/pause — Pause all monitoring\n"
        "/resume — Resume monitoring",
        parse_mode="Markdown"
    )

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addlink <url> <site_name>")
        return
    url = args[0]
    site_name = " ".join(args[1:])

    # Validate URL
    if not url.startswith("http"):
        await update.message.reply_text("❌ Invalid URL. Must start with http or https.")
        return

    try:
        db.insert("monitored_urls", {
            "url": url,
            "site_name": site_name,
            "active": True,
            "date_added": datetime.utcnow().isoformat()
        })
        await update.message.reply_text(f"✅ Added: {site_name}\n{url}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def removelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removelink <url>")
        return
    url = args[0]
    try:
        db.update("monitored_urls", {"url": f"eq.{url}"}, {"active": False})
        await update.message.reply_text(f"✅ Removed: {url}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def listlinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        urls = db.get("monitored_urls", {"active": "eq.true"})
        if not urls:
            await update.message.reply_text("No active URLs.")
            return
        msg = "📋 *Active URLs:*\n\n"
        for u in urls:
            msg += f"• {u['site_name']}\n  {u['url']}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        circulars = db.get("circulars", {})
        queue = db.get("notification_queue", {"resolved": "eq.false"})
        urls = db.get("monitored_urls", {"active": "eq.true"})
        msg = (
            f"📊 *System Status*\n\n"
            f"🌐 Sites monitored: {len(urls)}\n"
            f"📄 Total circulars: {len(circulars)}\n"
            f"📬 Pending queue: {len(queue)}\n"
            f"🕐 Checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        urls = db.get("monitored_urls", {"active": "eq.true"})
        for u in urls:
            db.update("monitored_urls", {"id": f"eq.{u['id']}"}, {"active": False})
        await update.message.reply_text("⏸ Monitoring paused.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    try:
        urls = db.get("monitored_urls", {})
        for u in urls:
            db.update("monitored_urls", {"id": f"eq.{u['id']}"}, {"active": True})
        await update.message.reply_text("▶️ Monitoring resumed.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ─── Main ────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("removelink", removelink))
    app.add_handler(CommandHandler("listlinks", listlinks))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    print("🤖 Admin bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()