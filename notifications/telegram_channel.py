import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

def send_message(text):
    """Send a message to the Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    response = requests.post(url, json=payload)
    return response.json()

def format_circular(circular):
    """Format a circular into a Telegram message."""
    urgency = circular.get("urgency", "normal")
    emoji = "🚨" if urgency == "urgent" else "🔔"

    title = circular.get("title", "No title")[:200]
    source = circular.get("source_site", "ESIC")
    date = circular.get("date_published", "N/A")
    circular_url = circular.get("circular_url", "")

    message = f"""
{emoji} *New ESIC Circular*

📄 *Title:* {title}
🏢 *Source:* {source}
📅 *Date:* {date}

🔗 [View Circular]({circular_url})

#ESIC #{source.replace(" ", "")}
""".strip()

    return message

def post_circular(circular):
    """Format and post a circular to Telegram channel."""
    try:
        message = format_circular(circular)
        result = send_message(message)

        if result.get("ok"):
            print(f"  ✅ Posted to Telegram: {circular['title'][:50]}...")
            time.sleep(1)
            return True
        else:
            print(f"  ❌ Telegram error: {result.get('description')}")
            return False

    except Exception as e:
        print(f"  ❌ Failed to post: {e}")
        return False

if __name__ == "__main__":
    # Test with a sample circular
    test_circular = {
        "title": "Test Circular — ESIC Monitor is Live!",
        "source_site": "ESIC HQ",
        "date_published": "2026-05-14",
        "circular_url": "https://esic.gov.in/circulars",
        "urgency": "normal"
    }
    print("Sending test message to channel...")
    result = post_circular(test_circular)
    if result:
        print("✅ Test successful — check your Telegram channel!")
    else:
        print("❌ Test failed")