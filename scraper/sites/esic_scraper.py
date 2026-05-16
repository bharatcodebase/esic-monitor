import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from bs4 import BeautifulSoup
from scraper.base_scraper import fetch_page, hash_url, log_event
import db.client as db
from datetime import datetime


# All sites to monitor with their column mappings
SITES = [
    {
        "url": "https://esic.gov.in/circulars",
        "name": "ESIC HQ",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5}
    },
    {
        "url": "https://dmd.esic.gov.in/circulars/esichospital_circular_list",
        "name": "ESIC DMD",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5}
    },
    {
        "url": "https://rodelhi.esic.gov.in/circulars/rosro_circular_list",
        "name": "ESIC RO Delhi",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5}
    },
    {
        "url": "https://esic.gov.in/newsevents",
        "name": "ESIC News & Events",
        "cols": {"branch": 1, "subject": 2, "date": 3, "console": 4}
    },
]


def circular_exists_by_console(console_no, source_site):
    """Check if circular already exists using console number + source site."""
    result = db.get("circulars", {
        "console_no": f"eq.{console_no}",
        "source_site": f"eq.{source_site}"
    })
    return len(result) > 0


def scrape_site(url, site_name, col_map):
    """Scrape circulars from any ESIC site using provided column mapping."""
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

        # Ensure minimum columns exist based on the highest index needed
        min_cols = max(col_map.values()) + 1
        if len(cols) < min_cols:
            continue

        try:
            # Extract data using column map
            branch = cols[col_map["branch"]].get_text(strip=True)
            publish_date = cols[col_map["date"]].get_text(strip=True)
            console_no = cols[col_map["console"]].get_text(strip=True)

            # Skip if no console number
            if not console_no:
                continue

            # Skip if already exists
            if circular_exists_by_console(console_no, site_name):
                continue

            # Get all PDF links from subject column
            subject_col = cols[col_map["subject"]]
            links = subject_col.find_all("a", href=True)

            if not links:
                continue

            # Collect all PDFs for this circular
            pdf_links = []
            main_title = ""

            for i, link in enumerate(links):
                title = link.get_text(strip=True)
                href = link["href"]

                # Build full URL if relative
                if href.startswith("/"):
                    base = "/".join(url.split("/")[:3])
                    pdf_url = base + href
                elif href.startswith("http"):
                    pdf_url = href
                else:
                    pdf_url = url + "/" + href

                # First link is the main title
                if i == 0:
                    main_title = title

                pdf_links.append({
                    "title": title,
                    "url": pdf_url
                })

            if not pdf_links:
                continue

            # Use console_no + site_name as unique hash
            url_hash = hash_url(console_no + site_name)

            circular_data = {
                "url_hash": url_hash,
                "title": main_title,
                "circular_url": pdf_links[0]["url"],
                "source_site": site_name,
                "branch": branch,
                "console_no": console_no,
                "pdf_links": json.dumps(pdf_links),
                "date_published": publish_date,
                "date_found": datetime.utcnow().isoformat(),
                "telegram_posted": False
            }

            new_circulars.append(circular_data)
            print(f"  ✅ New: [{console_no}] {main_title[:50]}... ({len(pdf_links)} PDFs)")

        except Exception as e:
            print(f"  ⚠️ Error parsing row: {e}")
            continue

    print(f"  📊 {len(new_circulars)} new circulars found on {site_name}")
    return new_circulars


if __name__ == "__main__":
    total = 0
    for site in SITES:
        circulars = scrape_site(site["url"], site["name"], site["cols"])
        for circular in circulars:
            try:
                db.insert("circulars", circular)
                total += 1
            except Exception as e:
                print(f"  ⚠️ Could not save: {e}")
    print(f"\n✅ Total new circulars saved: {total}")
