from machine import Pin
from time import sleep

# Relay module is ACTIVE LOW:
# LOW  = relay ON
# HIGH = relay OFF

RELAY_PIN = 13

relay = Pin(RELAY_PIN, Pin.OUT)

def relay_on():
    relay.value(0)
    print("Relay ON")

def relay_off():
    relay.value(1)
    print("Relay OFF")

# Start safely OFF
relay_off()
sleep(5)

while True:
    relay_on()
    sleep(1)

    relay_off()
    sleep(1)