# PROJECT OVERVIEW — SmartShelf (NYU Tandon SLDP)

## The problem this project solves
College students living in shared dorm rooms share a fridge.
Two problems come up constantly:
  1. Food gets taken by the wrong person (conflicts between roommates)
  2. Food gets forgotten and expires (food waste)

The SmartShelf is a laptop-sized wooden shelf that sits inside
the dorm fridge and solves both problems using sensors, a camera,
and a Raspberry Pi as the brain.

## How the full system works (team's flowchart)
Start
  → LCD screen always shows expiration dates + item weights
  → Wait for user to tap NFC card
  → Verify card UID against list of valid users
      → If invalid: show "Access Denied" on LCD screen
      → If valid: unlock servo motor (physical lock on shelf)
          → Read weight from HX711 load cell sensor
          → If weight changes (item taken or added):
              → USB camera starts recording the interaction
              → Store video + timestamp in that user's database record
          → If no weight change: loop back and keep reading
  → Close locker (servo locks again)

## Full hardware stack
- Raspberry Pi 4 (the brain — runs all the code)
- UCTRONICS 3.5" TFT LCD screen, 480x320px (displays UI)
- HX711 load cell weight sensor on GPIO pins DT=5, SCK=6
- RC522 NFC card reader (user authentication)
- Servo motor on GPIO PWM pin (physical lock/unlock)
- USB webcam (records interactions via OpenCV)
- Raspberry Pi OS Lite, accessed via SSH from laptop

## Team member responsibilities
- Minh (me): LCD screen UI + weight sensor logic + database logging
- Other teammates: NFC reader, servo motor, USB camera

## My 3 features to build

### Feature 1 — LCD Dashboard (index.html)
What the 3.5" screen always shows:
- "SMARTSHELF" title + live clock
- 3 shelf items, each with: name, weight bar, grams, status, expiry date
- Green bar + "OK" if weight is above threshold
- Red bar + "LOW" if weight is below threshold
- "Access Denied" or "Welcome [user]" message when NFC is tapped
- Footer: "NYU Tandon · SLDP 2025"

### Feature 2 — Weight Sensor Logic (sensor.py)
- Reads weight from HX711 every 2 seconds
- Compares new weight to previous weight
- If change > 5g: flags the event as significant
- Sets item status to "LOW" if weight drops below threshold
- Serves all item data as JSON via Flask API on port 5000
- index.html fetches from this API to update the display

### Feature 3 — Event Logger (database.py)
- Every time a significant weight change is detected:
    saves a log entry to logs/shelf_log.json containing:
    { timestamp, item_name, old_weight, new_weight, change_g, status }
- Only logs changes greater than 5g (filters out sensor noise)
- get_recent_logs(n) function returns the last n events
- sensor.py imports and calls this automatically
## File structure to generate
smartshelf/
├── index.html       # Feature 1: LCD UI
├── sensor.py        # Feature 2: weight logic + Flask API
├── database.py      # Feature 3: event logger
└── requirements.txt # flask, flask-cors

## IMPORTANT: mock data for now
I cannot connect the Pi yet (no SD card reader available).
All code must run on a regular Windows laptop for testing.

For sensor.py:
- DO NOT import RPi.GPIO or hx711 yet
- Instead, simulate weight with random fluctuations (±5–15g)
- Mark every mock section with a comment:
  # MOCK — replace with real HX711 code when on Pi

For index.html:
- Fetch from http://localhost:5000/api/weights every 2 seconds
- If fetch fails, fall back to hardcoded mock data silently
  so the UI still works even without sensor.py running

## Coding rules
- Plain Python 3 — no classes, no advanced patterns
- Plain HTML + CSS + JavaScript — no React, no npm, no build tools
- Every line or block must have a comment explaining what it does
- Keep each file under 80 lines — simple and readable
- This is a beginner-level school project, keep it approachable