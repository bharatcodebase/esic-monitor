import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from bs4 import BeautifulSoup
from scraper.base_scraper import fetch_page, hash_url, log_event
import db.client as db
from datetime import datetime


# All sites to monitor with their column mappings and pagination URL pattern
SITES = [
    {
        "url": "https://esic.gov.in/circulars",
        "name": "ESIC HQ",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5},
        "pagination_base": "https://esic.gov.in/circulars/index/page:"
    },
    {
        "url": "https://dmd.esic.gov.in/circulars/esichospital_circular_list",
        "name": "ESIC DMD",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5},
        "pagination_base": "https://dmd.esic.gov.in/Circulars/esic_hospital_circular_list/page:"
    },
    {
        "url": "https://rodelhi.esic.gov.in/circulars/rosro_circular_list",
        "name": "ESIC RO Delhi",
        "cols": {"branch": 1, "subject": 3, "date": 4, "console": 5},
        "pagination_base": "https://rodelhi.esic.gov.in/circulars/rosro_circular_list/page:"
    },
    {
        "url": "https://esic.gov.in/newsevents",
        "name": "ESIC News & Events",
        "cols": {"branch": 1, "subject": 2, "date": 3, "console": 4},
        "pagination_base": "https://esic.gov.in/NewsEvents/index/page:"
    },
]

MAX_PAGES = 3  # Maximum pages to scrape per site per run


def parse_date(date_str):
    """Convert DD/MM/YYYY to YYYY-MM-DD. Return as-is if already correct format."""
    try:
        if "/" in date_str:
            day, month, year = date_str.split("/")
            return f"{year}-{month}-{day}"
        return date_str
    except:
        return date_str


def circular_exists_by_console(console_no, source_site):
    """Check if circular already exists using console number + source site."""
    result = db.get("circulars", {
        "console_no": f"eq.{console_no}",
        "source_site": f"eq.{source_site}"
    })
    return len(result) > 0


def parse_page(html, url, site_name, col_map):
    """Parse a single page of circulars. Returns (new_circulars, total_rows)."""
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        print(f"  ❌ No table found on {site_name}")
        log_event("scrape", url, "failed", "No table found")
        return [], 0

    rows = table.find_all("tr")[1:]  # Skip header row
    if not rows:
        return [], 0

    print(f"  Found {len(rows)} rows")

    new_circulars = []
    min_cols = max(col_map.values()) + 1

    for row in rows:
        cols = row.find_all("td")

        if len(cols) < min_cols:
            continue

        try:
            branch = cols[col_map["branch"]].get_text(strip=True)
            publish_date = parse_date(cols[col_map["date"]].get_text(strip=True))
            console_no = cols[col_map["console"]].get_text(strip=True)

            if not console_no:
                continue

            if circular_exists_by_console(console_no, site_name):
                continue

            subject_col = cols[col_map["subject"]]
            links = subject_col.find_all("a", href=True)

            if not links:
                continue

            pdf_links = []
            main_title = ""

            for i, link in enumerate(links):
                title = link.get_text(strip=True)
                href = link["href"]

                if href.startswith("/"):
                    base = "/".join(url.split("/")[:3])
                    pdf_url = base + href
                elif href.startswith("http"):
                    pdf_url = href
                else:
                    pdf_url = url + "/" + href

                if i == 0:
                    main_title = title

                pdf_links.append({
                    "title": title,
                    "url": pdf_url
                })

            if not pdf_links:
                continue

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

    return new_circulars, len(rows)


def scrape_site(url, site_name, col_map, pagination_base):
    """Scrape circulars from any ESIC site with pagination support."""
    print(f"\n🔍 Scraping: {site_name}")

    all_new_circulars = []

    for page_num in range(1, MAX_PAGES + 1):
        # Build page URL
        if page_num == 1:
            page_url = url
        else:
            page_url = f"{pagination_base}{page_num}"

        print(f"  📄 Page {page_num}: {page_url}")

        html = fetch_page(page_url)
        if not html:
            print(f"  ❌ Could not fetch page {page_num} of {site_name}")
            break

        new_circulars, total_rows = parse_page(html, page_url, site_name, col_map)

        # Stop if empty table — no more pages exist
        if total_rows == 0:
            print(f"  ⏹ Page {page_num} is empty — stopping pagination")
            break

        all_new_circulars.extend(new_circulars)

        # Stop paginating if no new circulars on this page — rest will be older
        if len(new_circulars) == 0:
            print(f"  ⏹ No new circulars on page {page_num} — stopping pagination")
            break

        if page_num < MAX_PAGES:
            print(f"  ➡️ Found {len(new_circulars)} new — checking page {page_num + 1}")

    print(f"  📊 {len(all_new_circulars)} new circulars found on {site_name}")
    return all_new_circulars


if __name__ == "__main__":
    total = 0
    for site in SITES:
        circulars = scrape_site(site["url"], site["name"], site["cols"], site["pagination_base"])
        for circular in circulars:
            try:
                db.insert("circulars", circular)
                total += 1
            except Exception as e:
                print(f"  ⚠️ Could not save: {e}")
    print(f"\n✅ Total new circulars saved: {total}")
