import random      # for simulating sensor fluctuations
import time        # for sleeping between readings
import threading   # for running the sensor loop in the background
from flask import Flask, jsonify   # web server and JSON helper
from flask_cors import CORS        # lets index.html fetch from localhost:5000
import database    # our event logger (Feature 3)

# ============================================================
# SWITCH: set to True when running on the Raspberry Pi
#         set to False to run mock simulation on Windows
# ============================================================
USE_REAL_SENSOR = False

# --- HX711 pin numbers (matches your hardware wiring) ---
HX711_DT  = 5   # data pin on GPIO 5
HX711_SCK = 6   # clock pin on GPIO 6

# --- Calibration values — run calibrate.py on the Pi to get these ---
# Replace the two zeroes below after you calibrate your load cell
REFERENCE_UNIT = 0   # e.g. -370  (get from calibrate.py)
OFFSET         = 0   # e.g. -367471 (get from calibrate.py)

# --- Shelf item definitions ---
# Each item has a name, starting weight (grams), LOW threshold, and expiry date
ITEMS = [
    {"name": "Whole Milk",     "weight": 800, "threshold": 100, "expiry": "2026-05-01", "status": "OK"},
    {"name": "Cheddar Cheese", "weight": 200, "threshold":  50, "expiry": "2026-05-15", "status": "OK"},
    {"name": "Greek Yogurt",   "weight": 300, "threshold":  80, "expiry": "2026-04-20", "status": "OK"},
]

# Create Flask app and allow index.html to fetch from localhost
app = Flask(__name__)
CORS(app)

# --- Real HX711 setup (only runs on Pi when USE_REAL_SENSOR = True) ---
hx = None   # placeholder; gets assigned below if on Pi
if USE_REAL_SENSOR:
    from HX711 import SimpleHX711, Mass   # only available on Raspberry Pi
    hx = SimpleHX711(HX711_DT, HX711_SCK, REFERENCE_UNIT, OFFSET)
    hx.setUnit(Mass.Unit.G)   # read in grams
    hx.zero()                 # zero the scale before starting

# MOCK — replace with real HX711 code when on Pi
def simulate_reading(current_weight):
    # Add random noise between -15g and +15g to mimic sensor drift
    noise = random.uniform(-15, 15)
    return round(max(0, current_weight + noise), 1)   # weight can't go negative

def read_real_weight():
    # Read the median of 5 samples from the actual HX711 sensor
    grams = float(hx.weight(5))   # returns a Mass object; float() gives the number
    return round(grams, 1)

def sensor_loop():
    # Runs forever in the background — updates every 2 seconds
    while True:
        for item in ITEMS:
            old_w = item["weight"]

            if USE_REAL_SENSOR:
                new_w = read_real_weight()   # real sensor read
            else:
                new_w = simulate_reading(old_w)   # MOCK — replace when on Pi

            # Log to database if the weight changed more than 5g
            if abs(new_w - old_w) > 5:
                database.log_event(item["name"], old_w, new_w)

            # Update weight and set LOW/OK status against threshold
            item["weight"] = new_w
            item["status"] = "LOW" if new_w < item["threshold"] else "OK"

        time.sleep(2)   # pause 2 seconds before next reading

# API endpoint — index.html fetches this every 2 seconds
@app.route("/api/weights")
def get_weights():
    # Return all item data as a JSON list
    data = [
        {
            "name":   item["name"],
            "weight": item["weight"],
            "status": item["status"],
            "expiry": item["expiry"],
        }
        for item in ITEMS
    ]
    return jsonify(data)

# Start the sensor loop in a daemon thread
sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
sensor_thread.start()

# Run Flask server on port 5000
if __name__ == "__main__":
    app.run(port=5000, debug=False)
