from machine import Pin, I2C
import time
import ssd1306

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

count = 0
while True:
    oled.fill(0)
    oled.text("Count: {}".format(count), 0, 0)
    oled.show()
    print("Count:", count)
    count += 1
    time.sleep(1)