import requests
from config import SUPABASE_URL, SUPABASE_KEY

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

tables = ['monitored_urls', 'circulars', 'notification_queue', 'audit_log', 'user_preferences']

for table in tables:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(url, headers=headers)
    status = "✅" if response.status_code == 200 else "❌"
    print(f"{status} {table} — {response.status_code}")