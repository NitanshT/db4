# main.py — TCS34725 test
from machine import I2C, Pin
import time
from tcs34725 import TCS34725

# Adjust pins to your wiring. ESP32 common default: SCL=22, SDA=21.
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)

sensor = TCS34725(i2c)
sensor.integration_time(100)   # ms; longer = more sensitive, slower
sensor.gain(4)                 # 1, 4, 16, or 60

while True:
    r, g, b, c = sensor.read(raw=True)
    cct, lux = sensor.read()
    print("R={} G={} B={} C={}  CCT={:.0f}K  lux={:.1f}".format(
        r, g, b, c, cct, lux))
    time.sleep(1)