import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime, timedelta
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID
import db.client as db

def send_admin_message(text):
    """Send a message directly to admin's Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_ADMIN_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def daily_health_ping():
    """Send daily status report to admin."""
    try:
        # Get stats
        all_circulars = db.get("circulars", {})
        pending_queue = db.get("notification_queue", {"resolved": "eq.false"})
        active_urls = db.get("monitored_urls", {"active": "eq.true"})

        # Circulars found in last 24 hours
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        recent = [c for c in all_circulars if c.get("date_found", "") >= yesterday]

        # Build status message
        status = "✅ All systems operational"
        if len(pending_queue) > 10:
            status = "⚠️ High pending queue — check notifications"

        message = (
            f"🌅 *ESIC Monitor — Daily Status*\n\n"
            f"📊 Circulars (last 24h): {len(recent)}\n"
            f"💾 Total in DB: {len(all_circulars)}\n"
            f"📬 Pending queue: {len(pending_queue)}\n"
            f"🌐 Sites monitored: {len(active_urls)}\n"
            f"🕐 Report time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            f"{status}"
        )

        result = send_admin_message(message)
        if result.get("ok"):
            print("✅ Daily health ping sent.")
        else:
            print(f"❌ Failed to send ping: {result.get('description')}")

    except Exception as e:
        print(f"❌ Health check error: {e}")

def check_site_failures():
    """Alert admin if any site is failing repeatedly."""
    try:
        urls = db.get("monitored_urls", {"active": "eq.true"})
        for url in urls:
            fail_count = url.get("fail_count", 0)
            if fail_count >= 5:
                message = (
                    f"🚨 *Site Failure Alert*\n\n"
                    f"Site: {url['site_name']}\n"
                    f"URL: {url['url']}\n"
                    f"Consecutive failures: {fail_count}\n\n"
                    f"Please check the site manually."
                )
                send_admin_message(message)
                print(f"⚠️ Alert sent for {url['site_name']}")
    except Exception as e:
        print(f"❌ Failure check error: {e}")

def check_queue_buildup():
    """Alert if notification queue is growing too large."""
    try:
        pending = db.get("notification_queue", {"resolved": "eq.false"})
        if len(pending) > 10:
            message = (
                f"⚠️ *Queue Alert*\n\n"
                f"Pending notifications: {len(pending)}\n"
                f"Telegram posts may be failing.\n"
                f"Check the notification queue."
            )
            send_admin_message(message)
            print(f"⚠️ Queue alert sent: {len(pending)} pending")
    except Exception as e:
        print(f"❌ Queue check error: {e}")

if __name__ == "__main__":
    print("Running health checks...")
    daily_health_ping()
    check_site_failures()
    check_queue_buildup()
    print("Done.")