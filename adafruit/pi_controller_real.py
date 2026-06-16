"""PI temperature controller for ESP32 (MicroPython).

Reads temperature from therm1 (pin 36) via the Thermistor driver,
drives a peltier via PWM on pin 27.

Deploy:
    mpremote cp pi_controller.py :pi_controller.py

To run from main.py:
    from pi_controller import PIController
    ctrl = PIController(setpoint=20.0)
    ctrl.run()
"""

from machine import Pin, PWM
from thermistor import Thermistor
from calibration import PIN_36_ADC_LOOKUP
import utime

# ── Tunable gains (copy from simulation) ─────────────────────────────────────
Kp = 0.08
Ki = 0.002

# ── Hardware ──────────────────────────────────────────────────────────────────
THERM_PIN  = 36
PWM_PIN    = 27
PWM_FREQ   = 1000   # Hz — fast enough for peltier driver
SER_RES    = 9800   # measured series resistor (ohms)

# ── Loop timing ───────────────────────────────────────────────────────────────
DT_MS      = 1000   # control loop interval (ms)

# ── Log file ──────────────────────────────────────────────────────────────────
LOG_FILE   = 'pi_log.txt'


class PIController:
    def __init__(self, setpoint=20.0, kp=Kp, ki=Ki, verbose=True):
        self.setpoint = setpoint
        self.kp       = kp
        self.ki       = ki
        self.verbose  = verbose
        self._integral = 0.0

        self.therm = Thermistor(
            pin_no=THERM_PIN,
            adc_lookup=PIN_36_ADC_LOOKUP,
            ser_res=SER_RES,
        )
        self.pwm = PWM(Pin(PWM_PIN), freq=PWM_FREQ)
        self.pwm.duty(0)

        with open(LOG_FILE, 'a') as f:
            f.write('timestamp_ms,temperature_C,pwm_pct,error\n')

    def _step(self, temperature):
        dt = DT_MS / 1000.0
        error = self.setpoint - temperature
        self._integral += error * dt
        output = self.kp * error + self.ki * self._integral
        output = max(0.0, min(1.0, output))  # clamp 0–1
        return output, error

    def _set_pwm(self, output):
        # ESP32 PWM duty: 0–1023
        duty = int(output * 1023)
        self.pwm.duty(duty)

    def run(self):
        if self.verbose:
            print('PI controller running. Setpoint: {}°C'.format(self.setpoint))
            print('Kp={} Ki={}'.format(self.kp, self.ki))

        while True:
            temp = self.therm.read()
            if temp is None:
                print('Bad reading — skipping')
                utime.sleep_ms(DT_MS)
                continue

            pwm_output, error = self._step(temp)
            self._set_pwm(pwm_output)

            ts = utime.ticks_ms()
            pwm_pct = round(pwm_output * 100, 1)

            if self.verbose:
                print('t={}ms  T={:.2f}°C  err={:.2f}  PWM={}%'.format(
                    ts, temp, error, pwm_pct))

            with open(LOG_FILE, 'a') as f:
                f.write('{},{:.3f},{},{:.3f}\n'.format(ts, temp, pwm_pct, error))

            utime.sleep_ms(DT_MS)