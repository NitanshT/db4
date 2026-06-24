"""
main_offline.py - ESP32 bioreactor experiment controller (MicroPython), OFFLINE.

Identical behaviour to main.py EXCEPT: no Wi-Fi, no MQTT, no cloud publish.
All data is written to local CSV log files only.

State machine:
  BOOT       -> (no Wi-Fi) show ready screen
  WAIT_1     -> wait for button (GPIO19)
  SELFTEST   -> probe thermistor + LTR329, show results
  WAIT_2     -> wait for button
  PRIME      -> pump 3 s, then 5 s CH0 burst -> average -> log
  EXPERIMENT -> PI cooling loop @ setpoint 17 C on peltier PWM;
                every 15 min pump 1 s then 5 s CH0 burst -> log;
                button press -> machine.reset() (back to BOOT; logs overwritten)

Already on device: oled_display.py, ssd1306.py, LTR329.py, thermistor.py,
button.py, sensor_config.py, config.py.
"""

import time
from machine import Pin, PWM, reset
import utime
import gc
import micropython

import oled_display as disp
import button as btn
from LTR329 import LTR329
from thermistor import Thermistor

from sensor_config import (
    THERMISTOR_1_PIN, PIN36_ADC_LOOKUP,
    MOSFET_PWM, MOSFET_PWM_FREQ,
    Kp, Ki,
)

# --- Tunables ----------------------------------------------------------------
SETPOINT_C        = 17.0
PUMP_PIN          = 32          # active-HIGH: pin high = pump ON

CONTROL_PERIOD_MS = 1000        # PI loop period; Ki was tuned for dt = 1 s
PUMP_INTERVAL_S   = 15 * 60     # periodic pump during the experiment
PRIME_PUMP_S      = 3
EXP_PUMP_S        = 1
CH0_BURST_S       = 5           # CH0 averaging window after each pump

MIN_VALID_TEMP_C  = 5
MAX_VALID_TEMP_C  = 35
MAX_CONSEC_ERRORS = 5

# Logs - overwritten every boot ('w').
TEMP_LOG_FILE   = "temp_pwm_log.csv"
LIGHT_LOG_FILE  = "light_log.csv"
LOG_FLUSH_EVERY = 10

# --- Globals (initialised in main) -------------------------------------------
pwm   = None
pump  = None
therm = None
light = None
_integral = 0.0


# --- OLED helper -------------------------------------------------------------
def screen(*lines):
    """Write up to 6 short lines (<=16 chars) to the shared OLED."""
    disp._oled.fill(0)
    for i, ln in enumerate(lines[:6]):
        disp._oled.text(str(ln)[:16], 0, i * 10)
    disp._oled.show()


# --- Pump then CH0 burst -----------------------------------------------------
def pump_and_measure(pump_seconds, light_log):
    """Run pump, then average CH0 over CH0_BURST_S, log locally."""
    pump.value(1)
    screen("PUMP ON", "{} s".format(pump_seconds))
    time.sleep(pump_seconds)
    pump.value(0)

    screen("MEASURING CH0", "{} s window".format(CH0_BURST_S))
    light.active(True)                       # keep sensor awake across the burst
    deadline = utime.ticks_add(utime.ticks_ms(), CH0_BURST_S * 1000)
    total = 0
    n = 0
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        try:
            ch0, _ch1 = light.read(raw=True)
            total += ch0
            n += 1
        except Exception as e:
            print("ch0 read err:", e)        # e.g. saturation -> lower LIGHT_GAIN
    light.active(False)

    if n == 0:
        screen("LIGHT ERR", "no valid CH0")
        light_log.write("{},,0\n".format(time.time()))
        light_log.flush()
        return

    avg = total / n
    light_log.write("{},{:.2f},{}\n".format(time.time(), avg, n))
    light_log.flush()
    print("CH0 avg {:.2f}  n={}".format(avg, n))


# --- PI step (anti-windup; identical math to PID.py) -------------------------
def pi_step(temperature):
    global _integral
    dt = CONTROL_PERIOD_MS / 1000.0
    error = temperature - SETPOINT_C
    unclamped = Kp * error + Ki * (_integral + error * dt)
    output = max(0.0, min(1.0, unclamped))
    if output == unclamped or (output >= 1.0 and error < 0) or (output <= 0.0 and error > 0):
        _integral += error * dt
    return output, error


def set_pwm(output):
    pwm.duty(int(output * 1023))             # ESP32 legacy PWM: 0-1023


# --- Experiment loop ---------------------------------------------------------
def experiment_loop(temp_log, light_log):
    global _integral
    _integral = 0.0
    consec_errors = 0
    flush_count = 0
    exp_start = time.time()
    last_pump_ms = utime.ticks_ms()          # prime just ran; restart 15-min clock

    while True:
        loop_start = utime.ticks_ms()

        # 1) read + control
        try:
            temp = therm.read()
            if temp is None:
                raise ValueError("sensor None")
            if not (MIN_VALID_TEMP_C <= temp <= MAX_VALID_TEMP_C):
                raise ValueError("temp {} out of range".format(temp))
            output, error = pi_step(temp)
            set_pwm(output)
            consec_errors = 0
        except Exception as e:
            consec_errors += 1
            pwm.duty(0)
            screen("FAULT #{}".format(consec_errors), str(e)[:16], "duty -> 0")
            print("fault:", e)
            if consec_errors >= MAX_CONSEC_ERRORS:
                stop_and_reset(temp_log, light_log,
                               reason="{} faults".format(consec_errors))
            utime.sleep_ms(CONTROL_PERIOD_MS)
            continue

        # 2) local log every loop (full resolution)
        pwm_pct = output * 100.0
        temp_log.write("{},{:.3f},{:.1f},{:.3f}\n".format(
            time.time(), temp, pwm_pct, error))
        flush_count += 1
        if flush_count >= LOG_FLUSH_EVERY:
            temp_log.flush()
            flush_count = 0

        screen("RUNNING (offline)",
               "SP : {:.1f}C".format(SETPOINT_C),
               "T  : {:.2f}C".format(temp),
               "Err: {:.2f}".format(error),
               "PWM: {:.1f}%".format(pwm_pct),
               "t  : {}s".format(time.time() - exp_start))

        # 3) periodic pump + CH0
        if utime.ticks_diff(utime.ticks_ms(), last_pump_ms) >= PUMP_INTERVAL_S * 1000:
            pump_and_measure(EXP_PUMP_S, light_log)
            last_pump_ms = utime.ticks_ms()

        # 4) stop button -> power cycle
        if btn.check_for_press():
            stop_and_reset(temp_log, light_log, reason="button press")

        # 5) pace the loop
        elapsed = utime.ticks_diff(utime.ticks_ms(), loop_start)
        utime.sleep_ms(max(0, CONTROL_PERIOD_MS - elapsed))


# --- Shutdown ----------------------------------------------------------------
def stop_and_reset(temp_log, light_log, reason="button press"):
    pwm.duty(0)
    pump.value(0)
    for f in (temp_log, light_log):
        try:
            f.flush()
            f.close()
        except Exception:
            pass
    screen("STOPPED", reason[:16], "power cycling...")
    print("stopping:", reason)
    time.sleep(1)
    reset()                                  # reruns main.py -> BOOT; logs reopened 'w'


# --- Boot / orchestration ----------------------------------------------------
def main():
    global pwm, pump, therm, light

    # BOOT (no Wi-Fi)
    screen("OFFLINE MODE", "logging only", "no wifi/mqtt")
    time.sleep(1)

    # Hardware that cannot fail on construction
    pwm = PWM(Pin(MOSFET_PWM), freq=MOSFET_PWM_FREQ)
    pwm.duty(0)
    pump = Pin(PUMP_PIN, Pin.OUT)
    pump.value(0)
    therm = Thermistor(pin_no=THERMISTOR_1_PIN, adc_lookup=PIN36_ADC_LOOKUP)

    # WAIT 1
    screen("Ready (offline).", "Press button to", "self-test.")
    btn.wait_for_press()

    # SELF-TEST
    screen("SELF TEST", "...")
    t = therm.read()
    if t is None or not (MIN_VALID_TEMP_C <= t <= MAX_VALID_TEMP_C):
        screen("THERM FAIL", "T = {}".format(t), "check wiring")
        raise RuntimeError("thermistor self-test failed: {}".format(t))

    try:
        light = LTR329(disp._i2c, measurement_rate=100)
        ch0, _ch1 = light.read(raw=True)
    except Exception as e:
        screen("LIGHT FAIL", str(e)[:16], "check i2c")
        raise

    screen("Thermistor OK",
           "  {:.1f} C".format(t),
           "Light Sensor OK",
           "  i2c, CH0={}".format(ch0),
           "",
           "Press -> prime")
    print("selftest ok  T={:.2f}C  CH0={}".format(t, ch0))

    # WAIT 2
    btn.wait_for_press()

    # Logs (overwrite each power cycle)
    temp_log = open(TEMP_LOG_FILE, "w")
    temp_log.write("time_s,temp_C,pwm_pct,error\n")
    light_log = open(LIGHT_LOG_FILE, "w")
    light_log.write("time_s,ch0_avg,n_samples\n")

    # PRIME -> EXPERIMENT
    try:
        pump_and_measure(PRIME_PUMP_S, light_log)
        experiment_loop(temp_log, light_log)
    except Exception as e:
        stop_and_reset(temp_log, light_log, reason="fault: {}".format(e))


main()