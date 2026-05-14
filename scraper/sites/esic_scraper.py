import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bs4 import BeautifulSoup
from scraper.base_scraper import fetch_page, hash_url, circular_exists, log_event
import db.client as db
from datetime import datetime

def scrape_site(url, site_name):
    """Scrape circulars from any ESIC site."""
    print(f"\n🔍 Scraping: {site_name}")
    
    html = fetch_page(url)
    if not html:
        print(f"  ❌ Could not fetch {site_name}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    
    # Find the circulars table
    table = soup.find("table")
    if not table:
        print(f"  ❌ No table found on {site_name}")
        log_event("scrape", url, "failed", "No table found")
        return []

    rows = table.find_all("tr")[1:]  # Skip header row
    print(f"  Found {len(rows)} rows")

    new_circulars = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        try:
            branch = cols[1].get_text(strip=True)
            circular_no_date = cols[2].get_text(strip=True)
            publish_date = cols[4].get_text(strip=True)
            console_no = cols[5].get_text(strip=True) if len(cols) > 5 else ""

            # Get all PDF links in subject column
            subject_col = cols[3]
            links = subject_col.find_all("a", href=True)

            if not links:
                continue

            for link in links:
                title = link.get_text(strip=True)
                href = link["href"]

                # Build full URL if relative
                if href.startswith("/"):
                    base = "/".join(url.split("/")[:3])
                    circular_url = base + href
                elif href.startswith("http"):
                    circular_url = href
                else:
                    circular_url = url + "/" + href

                # Skip non-PDF links
                if not any(x in circular_url.lower() for x in [".pdf", "download", "view"]):
                    if not any(x in title.lower() for x in ["pdf", "circular", "order"]):
                        continue

                url_hash = hash_url(circular_url)

                # Skip if already exists
                if circular_exists(url_hash):
                    continue

                circular_data = {
                    "url_hash": url_hash,
                    "title": title,
                    "circular_url": circular_url,
                    "source_site": site_name,
                    "date_published": publish_date,
                    "date_found": datetime.utcnow().isoformat(),
                    "telegram_posted": False
                }

                new_circulars.append(circular_data)
                print(f"  ✅ New: {title[:60]}...")

        except Exception as e:
            print(f"  ⚠️ Error parsing row: {e}")
            continue

    print(f"  📊 {len(new_circulars)} new circulars found on {site_name}")
    return new_circulars


# All 3 sites to monitor
SITES = [
    {
        "url": "https://esic.gov.in/circulars",
        "name": "ESIC HQ"
    },
    {
        "url": "https://dmd.esic.gov.in/circulars/esichospital_circular_list",
        "name": "ESIC DMD"
    },
    {
        "url": "https://rodelhi.esic.gov.in/circulars/rosro_circular_list",
        "name": "ESIC RO Delhi"
    }
]


if __name__ == "__main__":
    total = 0
    for site in SITES:
        circulars = scrape_site(site["url"], site["name"])
        for circular in circulars:
            try:
                db.insert("circulars", circular)
                total += 1
            except Exception as e:
                print(f"  ⚠️ Could not save circular: {e}")
    print(f"\n✅ Total new circulars saved to DB: {total}")