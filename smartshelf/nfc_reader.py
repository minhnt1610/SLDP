"""
NFC Reader
----------
Polls the PN532 over I2C for Mifare/ISO14443 cards.
Calls a callback with the UID string when a card is detected.
Authorised card UIDs are stored in nfc_cards.json next to this file.
"""

import json
import os
import threading
import time
from typing import Callable

CARDS_FILE = os.path.join(os.path.dirname(__file__), "nfc_cards.json")
POLL_INTERVAL = 0.5   # seconds between scans

_authorized_uids: list[str] = []
_lock = threading.Lock()


# ── Persistent card storage ───────────────────────────────────────────────────

def _load_cards() -> list[str]:
    if os.path.exists(CARDS_FILE):
        try:
            with open(CARDS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_cards():
    with open(CARDS_FILE, "w") as f:
        json.dump(_authorized_uids, f, indent=2)


def load():
    """Load authorised UIDs from disk."""
    global _authorized_uids
    _authorized_uids = _load_cards()


def add_card(uid: str):
    with _lock:
        uid = uid.upper()
        if uid not in _authorized_uids:
            _authorized_uids.append(uid)
            _save_cards()
            print(f"[nfc] Card added: {uid}")


def remove_card(uid: str):
    with _lock:
        uid = uid.upper()
        if uid in _authorized_uids:
            _authorized_uids.remove(uid)
            _save_cards()
            print(f"[nfc] Card removed: {uid}")


def is_authorized(uid: str) -> bool:
    return uid.upper() in _authorized_uids


def get_cards() -> list[str]:
    return list(_authorized_uids)


# ── PN532 reader ──────────────────────────────────────────────────────────────

def _uid_to_str(uid) -> str:
    return ":".join(f"{b:02X}" for b in uid)


I2C_BUS = 20   # PN532 found on /dev/i2c-20


def _make_pn532():
    """Initialise the PN532 over I2C bus 20. Returns the pn532 object or None."""
    try:
        from adafruit_extended_bus import ExtendedI2C
        from adafruit_pn532.i2c import PN532_I2C

        i2c = ExtendedI2C(I2C_BUS)
        pn532 = PN532_I2C(i2c, debug=False)
        pn532.SAM_configuration()
        print(f"[nfc] PN532 ready on I2C bus {I2C_BUS}")
        return pn532
    except OSError as e:
        print(f"[nfc] I2C error on bus {I2C_BUS}: {e}")
        return None
    except ValueError as e:
        print(f"[nfc] PN532 not found on bus {I2C_BUS}: {e}")
        return None
    except Exception as e:
        print(f"[nfc] PN532 init failed: {e} — running in simulation mode")
        return None


def start_polling(on_valid: Callable[[str], None],
                  on_invalid: Callable[[str], None] | None = None):
    """
    Start background thread polling for NFC cards.

    on_valid(uid)   — called when an authorised card is scanned
    on_invalid(uid) — called when an unknown card is scanned (optional)
    """
    load()
    t = threading.Thread(target=_poll_loop,
                         args=(on_valid, on_invalid),
                         daemon=True)
    t.start()
    return t


def _poll_loop(on_valid: Callable[[str], None],
               on_invalid: Callable[[str], None] | None):
    pn532 = _make_pn532()
    last_uid = None

    while True:
        uid_str = _read_once(pn532)

        if uid_str and uid_str != last_uid:
            last_uid = uid_str
            print(f"[nfc] Card detected: {uid_str}")
            if is_authorized(uid_str):
                print(f"[nfc] Authorised ✓")
                on_valid(uid_str)
            else:
                print(f"[nfc] Unauthorised ✗")
                if on_invalid:
                    on_invalid(uid_str)
        elif not uid_str:
            last_uid = None   # card removed — allow re-scan next time

        time.sleep(POLL_INTERVAL)


def _read_once(pn532) -> str | None:
    """Return UID string if a card is present, else None."""
    if pn532 is None:
        return None   # simulation mode — no card
    try:
        uid = pn532.read_passive_target(timeout=0.1)
        if uid:
            return _uid_to_str(uid)
    except Exception as e:
        print(f"[nfc] Read error: {e}")
    return None
