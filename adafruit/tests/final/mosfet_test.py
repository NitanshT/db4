from machine import Pin
import utime

mosfet = Pin(33, Pin.OUT)

while True:
    mosfet.value(1)
    print("ON")
    utime.sleep(10)
    mosfet.value(0)
    print("OFF")
    utime.sleep(10)