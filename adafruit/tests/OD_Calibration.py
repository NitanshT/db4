from machine import Pin, I2C
import time
from LTR329 import LTR329

# ASSUMPTION: adjust if your I2C wiring differs
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = LTR329(i2c)

# ASSUMPTION: button leg A -> GPIO19, leg B -> GND, internal pull-up.
# Idle = 1 (HIGH), pressed = 0 (LOW).
button = Pin(19, Pin.IN, Pin.PULL_UP)

DEBOUNCE_MS = 50
OUTFILE = "Calibration Output.txt"


def wait_for_press():
    # Blocks until a clean press is detected, then blocks until release.
    while button.value() == 1:
        time.sleep_ms(10)
    time.sleep_ms(DEBOUNCE_MS)
    if button.value() != 0:
        return wait_for_press()  # was noise, retry
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(DEBOUNCE_MS)


def check_for_stop_press():
    if button.value() != 0:
        return False
    time.sleep_ms(DEBOUNCE_MS)
    if button.value() != 0:
        return False
    while button.value() == 0:
        time.sleep_ms(10)
    time.sleep_ms(DEBOUNCE_MS)
    return True


def main():
    print("Ready. Press button (GPIO19) to start measurement.")
    while True:
        wait_for_press()
        print("Measurement started.")

        sensor.active(True)  # keep sensor active for the whole run, see note below
        measurements = []
        t0 = time.ticks_ms()

        while True:
            ch0, ch1 = sensor.read(raw=True)
            t = time.ticks_diff(time.ticks_ms(), t0)
            measurements.append((t, ch0))
            print("t={}ms  ch0={}".format(t, ch0))

            if check_for_stop_press():
                break

        sensor.active(False)
        print("Measurement stopped. Saving {} samples.".format(len(measurements)))

        with open(OUTFILE, "w") as f:
            f.write("time_ms,ch0\n")
            for t, ch0 in measurements:
                f.write("{},{}\n".format(t, ch0))

        print("Saved to '{}'.".format(OUTFILE))
        print("Ready. Press button to start again.")


main()