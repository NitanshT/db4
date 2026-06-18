"""PI temperature controller for ESP32 (MicroPython).

Reads temperature from therm1 (pin 36) via the Thermistor driver,
drives a peltier via PWM on pin 33.

Deploy:
    mpremote cp pi_controller.py :pi_controller.py

To run from main.py:
    from pi_controller import PIController
    ctrl = PIController(setpoint=20.0)
    ctrl.run()
"""

from machine import Pin, PWM
from thermistor import Thermistor
from sensor_config import THERMISTOR_1_PIN, MOSFET_PWM, MOSFET_PWM_FREQ, Kp, Ki, PIN36_ADC_LOOKUP, PIN39_ADC_LOOKUP
import utime
import os


# ── Hardware ──────────────────────────────────────────────────────────────────
THERM_PIN  = THERMISTOR_1_PIN
PWM_PIN    = MOSFET_PWM
PWM_FREQ   = MOSFET_PWM_FREQ   # Hz — fast enough for peltier driver

# ── Loop timing ───────────────────────────────────────────────────────────────
DT_MS      = 1000   # control loop interval (ms)

# ── Sensor validity ───────────────────────────────────────────────────────────
MIN_VALID_TEMP_C = 5    # adjust to your real operating envelope
MAX_VALID_TEMP_C = 35

# ── Fault tolerance ───────────────────────────────────────────────────────────
MAX_CONSECUTIVE_ERRORS = 5   # stop the controller if this many bad cycles happen in a row

# ── Log file ──────────────────────────────────────────────────────────────────
LOG_FILE          = 'pi_log.txt'
LOG_FLUSH_EVERY_N = 10   # flush to flash every N writes, not every write


class PIController:
    def __init__(self, setpoint=17.0, kp=Kp, ki=Ki, verbose=True):
        self.setpoint = setpoint
        self.kp       = kp
        self.ki       = ki
        self.verbose  = verbose
        self._integral = 0.0

        self.therm = Thermistor(
            pin_no=THERM_PIN,
            adc_lookup=PIN36_ADC_LOOKUP
        )
        self.pwm = PWM(Pin(PWM_PIN), freq=PWM_FREQ)
        self.pwm.duty(0)
        self._write_header_if_needed()
        self._logfile = open(LOG_FILE, 'a')
        self._log_write_count = 0

    def _write_header_if_needed(self):
        try:
            size = os.stat(LOG_FILE)[6]
        except OSError:
            size = 0
        if size == 0:
            with open(LOG_FILE, 'a') as f:
                f.write('timestamp_s,temperature_C,pwm_pct,error\n')

    def _step(self, temperature):
        dt = DT_MS / 1000.0
        error = temperature - self.setpoint

        unclamped = self.kp * error + self.ki * (self._integral + error * dt)
        output = max(0.0, min(1.0, unclamped))

        # only integrate if not saturated, or if integrating would pull output back into range
        if output == unclamped or (output >= 1.0 and error < 0) or (output <= 0.0 and error > 0):
            self._integral += error * dt
        return output, error

    def _set_pwm(self, output):
        # ESP32 PWM duty: 0–1023
        duty = int(output * 1023)
        self.pwm.duty(duty)

    def _fail_safe(self, reason):
        self.pwm.duty(0)
        if self.verbose:
            print('FAULT — duty set to 0. Reason: {}'.format(reason))

    def _log(self, ts, temp, pwm_pct, error):
        self._logfile.write('{},{:.3f},{},{:.3f}\n'.format(ts, temp, pwm_pct, error))
        self._log_write_count += 1
        if self._log_write_count >= LOG_FLUSH_EVERY_N:
            self._logfile.flush()
            self._log_write_count = 0

    def run(self, max_iterations=None, stop_check=None, display=None):
        if self.verbose:
            print('PI controller running. Setpoint: {}°C'.format(self.setpoint))
            print('Kp={} Ki={}'.format(self.kp, self.ki))

        consecutive_errors = 0
        iteration = 0

        try:
            while max_iterations is None or iteration < max_iterations:
                iteration += 1
                loop_start = utime.ticks_ms()

                try:
                    temp = self.therm.read()
                    if temp is None:
                        raise ValueError('sensor returned None')
                    if not (MIN_VALID_TEMP_C <= temp <= MAX_VALID_TEMP_C):
                        raise ValueError('temperature {} outside valid range [{}, {}]'.format(
                            temp, MIN_VALID_TEMP_C, MAX_VALID_TEMP_C))

                    pwm_output, error = self._step(temp)
                    self._set_pwm(pwm_output)
                    consecutive_errors = 0

                    ts = utime.time()
                    pwm_pct = round(pwm_output * 100, 1)

                    if self.verbose:
                        print('t={}s  T={:.2f}°C  err={:.2f}  PWM={}%'.format(
                            ts, temp, error, pwm_pct))

                    if display is not None:
                        display.show_run(self.setpoint, temp, error, pwm_pct, iteration)

                    self._log(ts, temp, pwm_pct, error)

                except Exception as e:
                    consecutive_errors += 1
                    self._fail_safe(e)
                    if display is not None:
                        display.show_fault(e, consecutive_errors)
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        print('{} consecutive errors — stopping controller.'.format(consecutive_errors))
                        raise

                if stop_check is not None and stop_check():
                    if self.verbose:
                        print('Stop button pressed — shutting down.')
                    break

                elapsed = utime.ticks_diff(utime.ticks_ms(), loop_start)
                sleep_time = max(0, DT_MS - elapsed)
                utime.sleep_ms(sleep_time)

        finally:
            self.pwm.duty(0)
            self._logfile.flush()
            self._logfile.close()