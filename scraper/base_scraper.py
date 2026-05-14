import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import hashlib
import time
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime
from bs4 import BeautifulSoup
from config import MAX_RETRIES, RETRY_DELAYS
import db.client as db

def fetch_page(url):
    """Fetch a webpage with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  Fetching: {url} (attempt {attempt + 1})")
            response = requests.get(url, timeout=30, verify=False, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            })
            response.raise_for_status()
            log_event("scrape", url, "success", f"Fetched successfully")
            return response.text

        except Exception as e:
            log_event("scrape", url, "failed", f"Attempt {attempt+1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAYS[attempt]
                print(f"  Retrying in {wait} seconds...")
                time.sleep(wait)

    print(f"  ❌ Failed to fetch {url} after {MAX_RETRIES} attempts")
    return None

def hash_url(url):
    """Generate SHA256 hash of URL for duplicate detection."""
    return hashlib.sha256(url.strip().encode()).hexdigest()

def circular_exists(url_hash):
    """Check if circular already exists in DB."""
    result = db.get("circulars", {"url_hash": f"eq.{url_hash}"})
    return len(result) > 0

def detect_anomaly(url, previous_count, current_count):
    """Flag if circular count drops suddenly."""
    if previous_count > 5 and current_count < previous_count * 0.5:
        message = f"⚠️ Anomaly: {url} had {previous_count} circulars, now showing {current_count}"
        print(message)
        log_event("scrape", url, "anomaly", message)
        return True
    return False

def log_event(event_type, source_url=None, status="success", message=None):
    """Log every action to audit_log table."""
    try:
        db.insert("audit_log", {
            "event_type": event_type,
            "source_url": source_url,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"  Warning: Could not log event: {e}")

def get_active_urls():
    """Get all active URLs from DB."""
    return db.get("monitored_urls", {"active": "eq.true"})

def update_url_status(url_id, success=True):
    """Update last_checked and fail_count for a URL."""
    now = datetime.utcnow().isoformat()
    if success:
        db.update("monitored_urls", {"id": f"eq.{url_id}"}, {
            "last_checked": now,
            "last_success": now,
            "fail_count": 0
        })
    else:
        result = db.get("monitored_urls", {"id": f"eq.{url_id}"})
        if result:
            current_fails = result[0].get("fail_count", 0)
            db.update("monitored_urls", {"id": f"eq.{url_id}"}, {
                "last_checked": now,
                "fail_count": current_fails + 1
            })

if __name__ == "__main__":
    print("Testing base scraper...")
    html = fetch_page("https://esic.gov.in/circulars")
    if html:
        print(f"✅ Page fetched successfully — {len(html)} characters")
    else:
        print("❌ Failed to fetch page")