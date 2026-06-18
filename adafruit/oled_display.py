"""SSD1306 (128x64) display helper, shared I2C bus with other sensors.
Wiring: SCL=22, SDA=21, GND, 3.3V.
Prerequisite: ssd1306.py (the standard MicroPython driver) must already
be on the device. mpremote cp ssd1306.py :ssd1306.py if it isn't.
"""

from machine import Pin, I2C
import ssd1306

I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
OLED_WIDTH  = 128
OLED_HEIGHT = 64

_i2c  = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
_oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, _i2c)


def show_waiting():
    _oled.fill(0)
    _oled.text("Waiting for", 0, 0)
    _oled.text("button press to", 0, 10)
    _oled.text("start cooling", 0, 20)
    _oled.text("loop", 0, 30)
    _oled.show()


def show_run(setpoint, temp, error, pwm_pct, elapsed_iters):
    _oled.fill(0)
    _oled.text("RUNNING", 0, 0)
    _oled.text("SP : {:.1f}C".format(setpoint), 0, 10)
    _oled.text("T  : {:.2f}C".format(temp), 0, 20)
    _oled.text("Err: {:.2f}".format(error), 0, 30)
    _oled.text("PWM: {:.1f}%".format(pwm_pct), 0, 40)
    _oled.text("t  : {}s".format(elapsed_iters), 0, 50)
    _oled.show()


def show_fault(reason, count):
    msg = str(reason)
    _oled.fill(0)
    _oled.text("FAULT #{}".format(count), 0, 0)
    _oled.text(msg[:16], 0, 10)
    _oled.text(msg[16:32], 0, 20)
    _oled.text("duty -> 0", 0, 30)
    _oled.show()


def show_stopped(reason="button press"):
    _oled.fill(0)
    _oled.text("STOPPED", 0, 0)
    _oled.text(reason[:16], 0, 10)
    _oled.text("Reset/reflash", 0, 20)
    _oled.text("to run again.", 0, 30)
    _oled.show()