import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from config import SUPABASE_URL, SUPABASE_KEY
import requests
from config import SUPABASE_URL, SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
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

if __name__ == "__main__":
    print("✅ DB client ready")