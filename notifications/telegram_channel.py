import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
import json
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

# Heading map — add new sites here if needed
SITE_HEADINGS = {
    "ESIC News & Events": "New ESIC News & Event",
}
DEFAULT_HEADING = "New ESIC Circular"


def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    return response.json()


def format_circular(circular):
    urgency = circular.get("urgency", "normal")
    emoji = "🚨" if urgency == "urgent" else "🔔"

    source = circular.get("source_site", "ESIC")
    heading = SITE_HEADINGS.get(source, DEFAULT_HEADING)

    title = circular.get("title", "No title")
    branch = circular.get("branch", "")
    console_no = circular.get("console_no", "")
    date = circular.get("date_published", "N/A")

    # Build PDF links section
    pdf_links = circular.get("pdf_links", "[]")
    if isinstance(pdf_links, str):
        pdf_links = json.loads(pdf_links)

    docs_section = ""
    if pdf_links:
        docs_section = "\n\n📎 *Documents:*"
        for i, pdf in enumerate(pdf_links, 1):
            pdf_title = pdf["title"]
            pdf_url = pdf["url"]
            docs_section += f"\n{i}. [{pdf_title}]({pdf_url})"

    message = f"""{emoji} *{heading}*

🏢 *Branch:* {branch}
🔢 *Console No:* {console_no}
📅 *Published:* {date}
🏛 *Source:* {source}

📄 *Subject:* {title}{docs_section}

#ESIC #{source.replace(" ", "").replace("&", "")}""".strip()

    return message


def post_circular(circular):
    try:
        message = format_circular(circular)
        result = send_message(message)

        if result.get("ok"):
            print(f"  ✅ Posted to Telegram: {circular.get('console_no', '')} {circular['title'][:40]}...")
            time.sleep(1)
            return True
        else:
            print(f"  ❌ Telegram error: {result.get('description')}")
            return False

    except Exception as e:
        print(f"  ❌ Failed to post: {e}")
        return False


if __name__ == "__main__":
    test_circular = {
        "title": "Monitoring, Management, and Disposal of Near-Expiry Medicines",
        "source_site": "ESIC HQ",
        "branch": "RC Cell",
        "console_no": "25449/2026",
        "date_published": "2026-05-11",
        "urgency": "normal",
        "pdf_links": json.dumps([
            {"title": "Main Circular PDF", "url": "https://esic.gov.in/circular1.pdf"},
            {"title": "Enclosures Related Circular", "url": "https://esic.gov.in/circular2.pdf"},
            {"title": "Guidance document by CDSCO", "url": "https://esic.gov.in/circular3.pdf"}
        ])
    }
    print("Sending test message...")
    result = post_circular(test_circular)
    if result:
        print("✅ Test successful — check your Telegram channel!")
    else:
        print("❌ Test failed")
