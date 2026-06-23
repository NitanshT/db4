from machine import Pin
import time

button = Pin(19, Pin.IN, Pin.PULL_UP)

while True:
    if button.value() == 0:
        print("Button pressed")
    time.sleep_ms(50)