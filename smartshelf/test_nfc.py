"""Quick test for PN532 on I2C bus 20."""

import time
from adafruit_extended_bus import ExtendedI2C
from adafruit_pn532.i2c import PN532_I2C

print("Connecting to PN532 on I2C bus 20...")
i2c = ExtendedI2C(1)

pn532 = None
for attempt in range(5):
    try:
        time.sleep(1.0)
        print(f"Attempt {attempt + 1}...")
        pn532 = PN532_I2C(i2c, debug=False)
        pn532.SAM_configuration()
        print("PN532 ready!")
        break
    except RuntimeError as e:
        print(f"  Failed: {e}")
        pn532 = None

if pn532 is None:
    print("Could not initialise PN532 after 5 attempts.")
    print("Check: VCC wired to 5V (Pin 2), SDA=Pin 3, SCL=Pin 5, GND=Pin 6")
    exit(1)

print("Hold an NFC card to the reader...")
while True:
    uid = pn532.read_passive_target(timeout=0.5)
    if uid:
        print("Card UID:", ":".join(f"{b:02X}" for b in uid))
        print("Done! Copy this UID into nfc_cards.json to authorise it.")
        break
