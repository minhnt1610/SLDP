import random
import time
import threading
import json
import os
from flask import Flask, jsonify
from flask_cors import CORS
import database

USE_REAL_SENSOR = True

HX711_DT  = 5
HX711_SCK = 13
REFERENCE_UNIT = 106
OFFSET         = -26624

ITEMS_FILE = os.path.join(os.path.dirname(__file__), "items.json")
_lock = threading.Lock()
_weight_change_callbacks: list = []


def add_weight_change_callback(fn) -> None:
    """Register fn(item_name, old_weight, new_weight) — called on significant weight change."""
    _weight_change_callbacks.append(fn)

# ── Persistent storage ────────────────────────────────────────────────────────

def _default_items():
    return [
        {"name": "Whole Milk",     "weight": 800,  "threshold": 100, "expiry": "2026-05-01", "status": "OK"},
        {"name": "Cheddar Cheese", "weight": 200,  "threshold":  50, "expiry": "2026-05-15", "status": "OK"},
        {"name": "Greek Yogurt",   "weight": 300,  "threshold":  80, "expiry": "2026-04-20", "status": "OK"},
        {"name": "Whole Chicken",  "weight": 1200, "threshold": 200, "expiry": "2026-05-30", "status": "OK"},
    ]

def _load_items():
    if os.path.exists(ITEMS_FILE):
        try:
            with open(ITEMS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return _default_items()

def save_items():
    with open(ITEMS_FILE, "w") as f:
        json.dump(ITEMS, f, indent=2)

# ── CRUD helpers (called from display.py) ─────────────────────────────────────

def add_item(name: str, threshold: int, expiry: str, weight: float = 0.0):
    with _lock:
        ITEMS.append({"name": name, "weight": weight,
                      "threshold": threshold, "expiry": expiry, "status": "OK"})
        save_items()

def remove_item(name: str):
    with _lock:
        ITEMS[:] = [i for i in ITEMS if i["name"] != name]
        save_items()

def update_item(name: str, **kwargs):
    with _lock:
        for item in ITEMS:
            if item["name"] == name:
                item.update(kwargs)
                save_items()
                break

# ── Load on startup ───────────────────────────────────────────────────────────
ITEMS = _load_items()

# ── Sensor setup ──────────────────────────────────────────────────────────────
hx = None

def _init_sensor():
    global hx
    if not USE_REAL_SENSOR:
        return
    from HX711 import SimpleHX711, Mass
    _hx = SimpleHX711(HX711_DT, HX711_SCK, REFERENCE_UNIT, OFFSET)
    _hx.setUnit(Mass.Unit.G)
    hx = _hx

threading.Thread(target=_init_sensor, daemon=True).start()

def simulate_reading(current_weight):
    noise = random.uniform(-15, 15)
    return round(max(0, current_weight + noise), 1)

def read_real_weight():
    if hx is None:
        return 0.0
    grams = float(hx.weight(5))
    return round(grams, 1)

def _process_weight_change(item, new_w):
    old_w = item["weight"]
    if abs(new_w - old_w) < 5:
        return
    database.log_event(item["name"], old_w, new_w)
    for _cb in _weight_change_callbacks:
        try:
            _cb(item["name"], old_w, new_w)
        except Exception:
            pass
    with _lock:
        for i in ITEMS:
            if i["name"] == item["name"]:
                i["weight"] = new_w
                i["status"] = "LOW" if new_w < i["threshold"] else "OK"
                break


def sensor_loop():
    while True:
        with _lock:
            snapshot = list(ITEMS)

        if USE_REAL_SENSOR:
            # One physical scale — read once and apply to the first item only
            if snapshot:
                new_w = read_real_weight()
                _process_weight_change(snapshot[0], new_w)
        else:
            for item in snapshot:
                new_w = simulate_reading(item["weight"])
                _process_weight_change(item, new_w)

        time.sleep(2)

# ── Flask API ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

@app.route("/api/weights")
def get_weights():
    with _lock:
        data = [{"name": i["name"], "weight": i["weight"],
                 "status": i["status"], "expiry": i["expiry"]} for i in ITEMS]
    return jsonify(data)

sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
sensor_thread.start()

if __name__ == "__main__":
    app.run(port=5000, debug=False)
