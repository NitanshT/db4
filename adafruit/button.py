"""Debounced pushbutton on GPIO19.
Wiring: leg A -> GPIO19, leg B -> GND, internal pull-up.
Idle = HIGH (1), pressed = LOW (0).
"""

from machine import Pin
import utime

BUTTON_PIN  = 19
DEBOUNCE_MS = 50

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)


def wait_for_press():
    """Blocks until a clean press-and-release cycle completes."""
    while button.value() == 1:
        utime.sleep_ms(10)
    utime.sleep_ms(DEBOUNCE_MS)
    if button.value() != 0:
        return wait_for_press()  # was noise, retry
    while button.value() == 0:
        utime.sleep_ms(10)
    utime.sleep_ms(DEBOUNCE_MS)


def check_for_press():
    """Non-blocking when idle: one Pin read, returns False immediately.
    If currently pressed: blocks briefly through debounce + release,
    then returns True. Safe to call once per ~1Hz control loop iteration."""
    if button.value() != 0:
        return False
    utime.sleep_ms(DEBOUNCE_MS)
    if button.value() != 0:
        return False
    while button.value() == 0:
        utime.sleep_ms(10)
    utime.sleep_ms(DEBOUNCE_MS)
    return True