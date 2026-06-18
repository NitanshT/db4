"""Entry point. Wait for button -> run cooling loop -> button stops -> halt.
Power: wall-outlet supply to the ESP32, not laptop USB, for the full run.
"""

import utime
import oled_display as disp
import button as btn
from PID import PIController

SETPOINT_C = 17.0


def halt(reason="button press"):
    """Hard stop — does not return. Reset or re-flash the board to run again."""
    disp.show_stopped(reason)
    while True:
        utime.sleep_ms(1000)


def main():
    disp.show_waiting()
    btn.wait_for_press()

    ctrl = PIController(setpoint=SETPOINT_C, verbose=True)
    try:
        ctrl.run(stop_check=btn.check_for_press, display=disp)
        halt(reason="button press")
    except Exception as e:
        halt(reason="fault: {}".format(e))


main()