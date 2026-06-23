from machine import Pin, I2C
import utime
import ssd1306
from LTR329 import LTR329

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

BUTTON_PIN  = 19
PUMP_PIN    = 32        # dummy — rewire as needed
LOG_FILE    = "overnight_log.txt"

AVG_INTERVAL_MS  = 4 * 60 * 1000   # 5 minutes
PUMP_INTERVAL_MS = 15 * 1000        # 15 seconds
PUMP_ON_MS       = 1000             # 1 second

# -------------------------------------------------------------------
# HARDWARE
# -------------------------------------------------------------------

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
pump   = Pin(PUMP_PIN, Pin.OUT)
pump.value(0)

i2c  = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
sensor = LTR329(i2c)
sensor.active(True)

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def wait_for_button_release():
    while button.value() == 0:
        utime.sleep_ms(50)

def oled_msg(line1, line2=""):
    oled.fill(0)
    oled.text(line1, 0, 0)
    oled.text(line2, 0, 16)
    oled.show()

# -------------------------------------------------------------------
# WAIT FOR START
# -------------------------------------------------------------------

oled_msg("Waiting...", "Press to start")
print("Waiting for button press to start...")

while button.value() == 1:
    utime.sleep_ms(50)
wait_for_button_release()

print("Started.")

# -------------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------------

ch0_samples      = []
last_avg_ms      = utime.ticks_ms()
last_pump_ms     = utime.ticks_ms()
running          = True

with open(LOG_FILE, "a") as f:
    f.write("timestamp_ms,avg_ch0\n")

while running:

    now = utime.ticks_ms()

    # -- Stop check ------------------------------------------------
    if button.value() == 0:
        wait_for_button_release()
        print("Stop button pressed. Saving and shutting down.")
        running = False
        break

    # -- Read sensor -----------------------------------------------
    ch0, ch1 = sensor.read(raw=True)
    ch0_samples.append(ch0)
    print("CH0:", ch0)

    # -- Pump ------------------------------------------------------
    if utime.ticks_diff(now, last_pump_ms) >= PUMP_INTERVAL_MS:
        print("Pump ON")
        pump.value(1)
        utime.sleep_ms(PUMP_ON_MS)
        pump.value(0)
        print("Pump OFF")
        last_pump_ms = utime.ticks_ms()

    # -- Average & log ---------------------------------------------
    if utime.ticks_diff(now, last_avg_ms) >= AVG_INTERVAL_MS:
        avg = sum(ch0_samples) / len(ch0_samples)
        ch0_samples = []
        last_avg_ms = utime.ticks_ms()
        print("Avg CH0 over last 5 min: {:.2f}".format(avg))
        oled_msg("Avg CH0:", "{:.2f}".format(avg))
        with open(LOG_FILE, "a") as f:
            f.write("{},{:.2f}\n".format(now, avg))
        print("Logged.")

    utime.sleep(1)

# -------------------------------------------------------------------
# SHUTDOWN
# -------------------------------------------------------------------

pump.value(0)
oled_msg("Done.", "File saved.")
print("Shutdown complete. Log at:", LOG_FILE)