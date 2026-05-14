import os
from dotenv import load_dotenv

load_dotenv()

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID") or "0")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Drive
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Scraper settings
SCRAPE_INTERVAL_MINUTES = 20
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]

# Notification settings
MAX_QUEUE_RETRIES = 5
BATCH_THRESHOLD = 20

# Bot settings
RATE_LIMIT_PER_MINUTE = 10
AUTO_BAN_AFTER = 20