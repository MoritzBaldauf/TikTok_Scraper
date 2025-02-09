# Directory for storing scraped data
DATA_DIR = "tiktok_data"

# File names for storing metrics
ACCOUNT_METRICS_FILE = "account_metrics.csv"
VIDEO_METRICS_FILE = "video_metrics.csv"

# Browser settings
HEADLESS_MODE = False  # Set to True for headless mode
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Timeouts and thresholds
DEFAULT_TIMEOUT = 30000  # 30 seconds in milliseconds
SHARE_TIMEOUT = 5000
NEW_VIDEO_THRESHOLD = 10  # Hours to consider a video as "new"

# Rate limiting
MIN_DELAY = 3  # Minimum delay between requests in seconds
MAX_DELAY = 10  # Maximum delay between requests in seconds

# Session managment
MAX_SESSION_RETRIES = 3  # Maximum number of session rotations per request
SESSION_ROTATION_DELAY = (5, 15)  # Random delay range between rotations in seconds

# Content filtering
EXCLUDE_PINNED_VIDEOS = True  # Set to True to exclude pinned videos from collection

SHEETS_CREDS = "./credentials/credentials.json"  # Path to your Google Sheets credentials
SPREADSHEET_ID = "1gPiwtjbz7_sRDrUAfmzqWRI2IlRUwoeIFQ9gIPosJQs"  # Your Google Sheets spreadsheet ID
ACCOUNTS = ["luminews.my", "boom.malaysia", "carlsonchia_oe", "dagangnews", "ohbulanofficial", "majoritiofficial", "wekaypoh", "goodnewsfromindonesia", "baseless.indo", "uzoneindonesia", "joyalcala_26", "rappler"]  # Your TikTok accounts
INTERVAL_HOURS = 12  # Hours between runs