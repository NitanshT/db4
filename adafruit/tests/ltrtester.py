import time
from machine import Pin, SoftI2C
from ltr329 import LTR329

# Adjust pins to your wiring
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100_000)

print("I2C scan:", [hex(a) for a in i2c.scan()])  # expect 0x29

sensor = LTR329(i2c, gain=1, integration_time=100, measurement_rate=500)
print("part ok, gain:", sensor.gain(), "meas:", sensor.measurement())

# 1. Raw channel read
ch0, ch1 = sensor.read(raw=True)
print("raw  ch0 (vis+IR): {}  ch1 (IR): {}".format(ch0, ch1))

# 2. Continuous lux readout
sensor.active(True)
try:
    while True:
        lux = sensor.read()
        ch0, ch1 = sensor.read(raw=True)
        ratio = ch1 / (ch0 + ch1) if (ch0 + ch1) else 0
        print("lux: {:8.2f}   ch0: {:5d}  ch1: {:5d}  IR ratio: {:.2f}".format(
            lux, ch0, ch1, ratio))
        time.sleep(1)
except KeyboardInterrupt:
    sensor.active(False)
    print("stopped")