from machine import Pin, I2C
from LTR329 import LTR329
import utime

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
sensor = LTR329(i2c)
sensor.active(True)

while True:
    ch0, ch1 = sensor.read(raw=True)
    print("CH0:", ch0)
    utime.sleep(1)