import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from config import SUPABASE_URL, SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json"
}

def get(table, filters=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = filters or {}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {**HEADERS, "Prefer": "return=minimal"}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return True

def update(table, filters, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.patch(url, headers=HEADERS, params=filters, json=data)
    response.raise_for_status()
    return True

def count(table, filters=None):
    """Return exact row count via PostgREST count header — no 1000-row ceiling."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    params = filters or {}
    headers = {**HEADERS, "Prefer": "count=exact", "Range": "0-0"}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    content_range = response.headers.get("Content-Range", "")
    if "/" in content_range:
        total = content_range.split("/")[-1]
        if total.isdigit():
            return int(total)
    return len(response.json())

if __name__ == "__main__":
    print("✅ DB client ready")