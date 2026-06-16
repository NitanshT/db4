from machine import Pin, I2C
import time

PIN_SETS = [
    (0, 22, 23),  # Huzzah32 / Adafruit-style: SCL 22, SDA 23
    (0, 22, 21),  # Common ESP32 default: SCL 22, SDA 21
    (1, 22, 23),
    (1, 22, 21),
]

for bus_id, scl_pin, sda_pin in PIN_SETS:
    try:
        print()
        print("Testing I2C bus", bus_id, "SCL", scl_pin, "SDA", sda_pin)

        i2c = I2C(
            bus_id,
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=100000
        )

        devices = i2c.scan()

        if devices:
            print("Found:", [hex(addr) for addr in devices])
        else:
            print("Found: nothing")

        time.sleep(0.5)

    except Exception as e:
        print("Error:", e)