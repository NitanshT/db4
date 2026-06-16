from machine import Pin, I2C
import time
import math
import ssd1306

# -------------------------------------------------------------------
# I2C + OLED SETUP
# -------------------------------------------------------------------

I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
OLED_ADDR = 0x3C
I2C_FREQ = 100000

OLED_WIDTH = 128
OLED_HEIGHT = 64

i2c = I2C(
    0,
    scl=Pin(22),
    sda=Pin(21),
    freq=100000
)

print("I2C devices found:", [hex(addr) for addr in i2c.scan()])

oled = ssd1306.SSD1306_I2C(
    128,
    64,
    i2c,
    addr=0x3C
)

# -------------------------------------------------------------------
# TEST STATE
# -------------------------------------------------------------------

test_number = 1
test_start_ms = time.ticks_ms()

# Example: 60 means every 60 seconds
TEST_DURATION_S = 60


# -------------------------------------------------------------------
# SENSOR PLACEHOLDERS
# I'll replace them later
# -------------------------------------------------------------------

def read_temp_mussels():
    # Replace with thermistor 1 reading
    return 17.6


def read_temp_algae():
    # Replace with thermistor 2 reading
    return 18.1


def read_od_water():
    # Replace with actual OD calculation 
    return 0.42


# -------------------------------------------------------------------
# DISPLAY HELPERS
# -------------------------------------------------------------------

def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return "{:02d}:{:02d}".format(minutes, seconds)


def get_elapsed_seconds():
    elapsed_ms = time.ticks_diff(time.ticks_ms(), test_start_ms)
    return elapsed_ms // 1000


def start_new_test():
    global test_number, test_start_ms

    test_number += 1

    if test_number > 99:
        test_number = 1

    test_start_ms = time.ticks_ms()


def update_oled(temp1, temp2, od):
    elapsed_s = get_elapsed_seconds()

    oled.fill(0)

    oled.text("Test {:02d}".format(test_number), 0, 0)
    oled.text("Time {}".format(format_time(elapsed_s)), 0, 10)

    oled.hline(0, 21, 128, 1)

    oled.text("T1 Muss:{:5.1f}C".format(temp1), 0, 25)
    oled.text("T2 Alg :{:5.1f}C".format(temp2), 0, 37)
    oled.text("OD H2O :{:5.2f}".format(od), 0, 49)

    oled.show()


# -------------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------------

while True:
    elapsed_s = get_elapsed_seconds()

    if elapsed_s >= TEST_DURATION_S:
        start_new_test()

    temp1 = read_temp_mussels()
    temp2 = read_temp_algae()
    od_water = read_od_water()

    update_oled(temp1, temp2, od_water)

    time.sleep(1)