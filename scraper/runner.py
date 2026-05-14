import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db.client as db
from scraper.sites.esic_scraper import scrape_site, SITES
from scraper.base_scraper import log_event
from datetime import datetime

def add_to_notification_queue(circular_id):
    """Add newly found circular to notification queue."""
    try:
        db.insert("notification_queue", {
            "circular_id": circular_id,
            "attempt_count": 0,
            "resolved": False
        })
    except Exception as e:
        print(f"  ⚠️ Could not add to queue: {e}")

def get_saved_circular_id(url_hash):
    """Get the DB id of a saved circular."""
    result = db.get("circulars", {"url_hash": f"eq.{url_hash}"})
    if result:
        return result[0]["id"]
    return None

def run():
    print(f"\n{'='*50}")
    print(f"🚀 Runner started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*50}")

    total_new = 0

    for site in SITES:
        # Scrape the site
        new_circulars = scrape_site(site["url"], site["name"])

        for circular in new_circulars:
            try:
                # Save to DB
                db.insert("circulars", circular)

                # Add to notification queue
                circular_id = get_saved_circular_id(circular["url_hash"])
                if circular_id:
                    add_to_notification_queue(circular_id)
                    total_new += 1
                    print(f"  📬 Queued for Telegram: {circular['title'][:50]}...")

            except Exception as e:
                print(f"  ⚠️ Error saving circular: {e}")
                log_event("error", site["url"], "failed", str(e))

    print(f"\n{'='*50}")
    print(f"✅ Run complete. {total_new} new circulars queued.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    run()