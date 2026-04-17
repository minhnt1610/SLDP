"""
Door Controller
---------------
Controls the FS90R continuous servo to open/close a door latch.
The FS90R has no position feedback — it runs at speed for a set duration.
"""

import time
import threading

SERVO_PIN     = 18      # GPIO 18 (hardware PWM, Pin 12)
SERVO_FREQ    = 50      # Hz

# Duty cycles for FS90R (adjust OPEN_DC/CLOSE_DC if direction is wrong)
STOP_DC       = 7.5     # neutral — servo stops
OPEN_DC       = 10.0    # spin one direction (open)
CLOSE_DC      = 5.0     # spin other direction (close)
MOVE_SECONDS  = 1.0     # how long to spin when opening/closing

_pwm = None
_lock = threading.Lock()
_door_open = False      # tracks current state

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    _GPIO_AVAILABLE = False
    print("[door] RPi.GPIO not available — servo will be simulated")


def setup():
    """Call once at startup to initialise the GPIO and PWM."""
    global _pwm
    if not _GPIO_AVAILABLE:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    _pwm = GPIO.PWM(SERVO_PIN, SERVO_FREQ)
    _pwm.start(STOP_DC)


def _spin(duty: float, seconds: float):
    """Spin the servo at duty cycle for the given number of seconds, then stop."""
    if _pwm:
        _pwm.ChangeDutyCycle(duty)
        time.sleep(seconds)
        _pwm.ChangeDutyCycle(STOP_DC)
    else:
        direction = "OPEN" if duty == OPEN_DC else "CLOSE"
        print(f"[door] [SIM] servo spinning {direction} for {seconds}s")
        time.sleep(seconds)
        print("[door] [SIM] servo stopped")


def open_door():
    global _door_open
    with _lock:
        if _door_open:
            return
        print("[door] Opening...")
        _spin(OPEN_DC, MOVE_SECONDS)
        _door_open = True
        print("[door] Open")


def close_door():
    global _door_open
    with _lock:
        if not _door_open:
            return
        print("[door] Closing...")
        _spin(CLOSE_DC, MOVE_SECONDS)
        _door_open = False
        print("[door] Closed")


def toggle_door():
    """Open if closed, close if open."""
    if _door_open:
        close_door()
    else:
        open_door()


def is_open() -> bool:
    return _door_open


def cleanup():
    """Release GPIO resources — call on shutdown."""
    if _pwm:
        _pwm.stop()
    if _GPIO_AVAILABLE:
        GPIO.cleanup()
