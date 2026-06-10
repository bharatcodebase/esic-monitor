import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db.client as db
from scraper.sites.esic_scraper import scrape_site, SITES
from scraper.base_scraper import log_event
from datetime import datetime
from notifications.telegram_channel import post_circular
from ai.summarizer import generate_summary
from config import MAX_QUEUE_RETRIES


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


def process_queue():
    """Re-send notifications that failed on a previous run (safety net)."""
    try:
        pending = db.get("notification_queue", {"resolved": "eq.false"})
    except Exception as e:
        print(f"  ⚠️ Could not read notification queue: {e}")
        return

    if not pending:
        return

    print(f"\n🔁 Retrying {len(pending)} unresolved notification(s)...")

    for item in pending:
        attempt = item.get("attempt_count", 0)
        circular_id = item.get("circular_id")

        # Give up after MAX_QUEUE_RETRIES — auto-clear and record why
        if attempt >= MAX_QUEUE_RETRIES:
            db.update("notification_queue",
                {"circular_id": f"eq.{circular_id}"},
                {
                    "resolved": True,
                    "failed": True,
                    "last_error": f"Gave up after {MAX_QUEUE_RETRIES} attempts"
                })
            log_event("error", None, "failed",
                      f"Notification permanently failed for circular {circular_id}")
            print(f"  🛑 Gave up on circular {circular_id} after {MAX_QUEUE_RETRIES} attempts")
            continue

        result = db.get("circulars", {"id": f"eq.{circular_id}"})
        if not result:
            print(f"  ⚠️ Circular {circular_id} not found — skipping")
            continue

        success = post_circular(result[0])
        if success:
            db.update("notification_queue",
                {"circular_id": f"eq.{circular_id}"},
                {"resolved": True})
            print(f"  ✅ Retry delivered: circular {circular_id}")
        else:
            db.update("notification_queue",
                {"circular_id": f"eq.{circular_id}"},
                {"attempt_count": attempt + 1})
            print(f"  ❌ Retry {attempt + 1}/{MAX_QUEUE_RETRIES} failed: circular {circular_id}")


def run():
    print(f"\n{'='*50}")
    print(f"🚀 Runner started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*50}")

    # Safety net: re-send any notifications that failed on a previous run
    process_queue()

    total_new = 0

    for site in SITES:
        # Scrape the site — pass col_map and pagination_base from SITES config
        new_circulars = scrape_site(
            site["url"],
            site["name"],
            site["cols"],
            site["pagination_base"]
        )

        for circular in new_circulars:
            try:
                # Generate bilingual AI summary (best-effort — never blocks posting)
                summary = generate_summary(circular)
                if summary:
                    circular["summary_en"] = summary["summary_en"]
                    circular["summary_hi"] = summary["summary_hi"]

                # Save to DB
                db.insert("circulars", circular)

                # Add to notification queue
                circular_id = get_saved_circular_id(circular["url_hash"])
                if circular_id:
                    add_to_notification_queue(circular_id)
                    total_new += 1
                    print(f"  📬 Queued for Telegram: {circular['title'][:50]}...")
                    success = post_circular(circular)
                    if success:
                        db.update("notification_queue",
                            {"circular_id": f"eq.{circular_id}"},
                            {"resolved": True})

            except Exception as e:
                print(f"  ⚠️ Error saving circular: {e}")
                log_event("error", site["url"], "failed", str(e))

    print(f"\n{'='*50}")
    print(f"✅ Run complete. {total_new} new circulars queued.")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
