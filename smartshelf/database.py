import json                      # for reading and writing JSON files
import os                        # for file path operations
from datetime import datetime    # for generating timestamps

# Path to the log file — stored inside a logs/ subfolder
LOG_DIR  = "logs"
LOG_FILE = os.path.join(LOG_DIR, "shelf_log.json")

# Minimum weight change (grams) required to log an event
NOISE_THRESHOLD = 5

def log_event(item_name, old_weight, new_weight):
    # Calculate how much the weight changed
    change = round(new_weight - old_weight, 1)

    # Ignore tiny fluctuations — only log real events (> 5g change)
    if abs(change) <= NOISE_THRESHOLD:
        return

    # Build the log entry as a dictionary
    entry = {
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "item_name":  item_name,
        "old_weight": old_weight,
        "new_weight": new_weight,
        "change_g":   change,
        "status":     "LOW" if new_weight < 50 else "OK",
    }

    # Create the logs/ folder if it doesn't already exist
    os.makedirs(LOG_DIR, exist_ok=True)

    # Load existing log entries from file, or start a fresh empty list
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    # Add the new entry to the list and save everything back to disk
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

def get_recent_logs(n=10):
    # Return the last n log entries; return empty list if file doesn't exist yet
    if not os.path.exists(LOG_FILE):
        return []

    # Read all entries and slice the last n
    with open(LOG_FILE, "r") as f:
        logs = json.load(f)
    return logs[-n:]
