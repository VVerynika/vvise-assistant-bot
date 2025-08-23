import os

# Priority users and channels
HIGH_PRIORITY_SLACK_USER = os.getenv("HIGH_PRIORITY_SLACK_USER", "dberes")
IMPORTANT_SLACK_CHANNEL_BUGS = os.getenv("IMPORTANT_SLACK_CHANNEL_BUGS", "bugs-ios")

# Telegram notifications
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID")  # e.g., numeric chat id as string

# Time thresholds (seconds)
UNANSWERED_HOURS = int(os.getenv("UNANSWERED_HOURS", "48"))
UNANSWERED_SECONDS = UNANSWERED_HOURS * 3600
DEADLINE_SOON_HOURS = int(os.getenv("DEADLINE_SOON_HOURS", "6"))
DEADLINE_SOON_SECONDS = DEADLINE_SOON_HOURS * 3600

# Cleanup policy
CLEANUP_PRIORITY_MAX = int(os.getenv("CLEANUP_PRIORITY_MAX", "10"))
CLEANUP_NO_RESPONSE_SECS = int(os.getenv("CLEANUP_NO_RESPONSE_SECS", str(UNANSWERED_SECONDS)))
CLEANUP_OLDER_THAN_DAYS = int(os.getenv("CLEANUP_OLDER_THAN_DAYS", "30"))
CLEANUP_RETENTION_DAYS = int(os.getenv("CLEANUP_RETENTION_DAYS", "7"))

# Storage files
SLACK_STATE_FILE = os.getenv("SLACK_STATE_FILE", "/workspace/.slack_state.json")
CLICKUP_STATE_FILE = os.getenv("CLICKUP_STATE_FILE", "/workspace/.clickup_state.json")
STORAGE_DB_FILE = os.getenv("STORAGE_DB_FILE", "/workspace/.vvise_assistant_store.json")

# Language/analysis
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.65"))

# Feature flags
ENABLE_SLACK = os.getenv("SLACK_TOKEN") is not None
ENABLE_CLICKUP = os.getenv("CLICKUP_API_TOKEN") is not None and os.getenv("CLICKUP_FOLDER_ID") is not None
ENABLE_TELEGRAM = os.getenv("TELEGRAM_TOKEN") is not None
ENABLE_SHEETS = os.getenv("GOOGLE_SHEET_ID") is not None and (os.getenv("GOOGLE_CREDS_JSON") is not None or os.getenv("SERVICE_ACCOUNT_JSON_PATH") is not None or os.getenv("RENDER_SECRET_FILE_SERVICE_ACCOUNT_JSON") is not None)