import network, time, math
from machine import Pin, ADC, I2C
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASS, AIO_USER, AIO_KEY
from adafruit.tcs34725 import TCS34725

# ---------------------------------------------------------------------------
# TIMING
# ---------------------------------------------------------------------------
SAMPLE_INTERVAL  = 2     # seconds between individual measurements
PUBLISH_INTERVAL = 30    # seconds between publishes (see rate-limit note below)

# ---------------------------------------------------------------------------
# THERMISTOR CONSTANTS  --  YOU MUST SET THESE TO MATCH YOUR CIRCUIT
# These are placeholders. I cannot know your hardware. Wrong values =
# plausible-but-wrong temperatures, which is worse than a crash.
# ---------------------------------------------------------------------------
R_FIXED = 10000.0        # the fixed resistor in your divider, ohms
R0      = 10000.0        # thermistor nominal resistance at 25 C, ohms
BETA    = 3950.0         # thermistor beta coefficient (from datasheet)
T0      = 298.15         # 25 C expressed in kelvin
# Divider orientation. True  = 3V3 -- R_FIXED -- [ADC node] -- thermistor -- GND
#                      False = 3V3 -- thermistor -- [ADC node] -- R_FIXED -- GND
THERMISTOR_ON_LOW_SIDE = True
ADC_FULL = 65535.0       # read_u16() full-scale

# ---------------------------------------------------------------------------
# WIFI
# ---------------------------------------------------------------------------
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        t = 0
        while not wlan.isconnected():
            time.sleep(1)
            t += 1
            print("wifi waiting...", wlan.status())
            if t > 20:
                raise RuntimeError("wifi failed, status: %d" % wlan.status())
    print("wifi ok", wlan.ifconfig())
    return wlan

# ---------------------------------------------------------------------------
# HARDWARE INIT
# ---------------------------------------------------------------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)   # set pins to your wiring
light = TCS34725(i2c)
light.integration_time(100)   # ms
light.gain(4)                 # 1, 4, 16, 60

# GPIO 36 and 39 are ADC1 channels. Required: ADC2 cannot be read while WiFi
# is active, so ADC1 is the only correct choice here.
t1 = ADC(Pin(36)); t1.atten(ADC.ATTN_11DB)   # ~0-3.3V range
t2 = ADC(Pin(39)); t2.atten(ADC.ATTN_11DB)

# ---------------------------------------------------------------------------
# READ FUNCTIONS
# ---------------------------------------------------------------------------
def read_lux():
    # Compute the luminance (y) term directly from raw channels.
    # Avoids the CCT division-by-zero in _temperature_and_lux when the
    # reactor is dark (clear channel near 0).
    r, g, b, c = light.read(raw=True)
    y = -0.32466 * r + 1.57837 * g + -0.73191 * b
    return max(0.0, y)

def adc_to_celsius(raw):
    # Guard against a railed reading (disconnected probe / short).
    if raw < 100 or raw > 65435:
        return None
    frac = raw / ADC_FULL
    if THERMISTOR_ON_LOW_SIDE:
        rth = R_FIXED * frac / (1.0 - frac)
    else:
        rth = R_FIXED * (1.0 - frac) / frac
    inv_t = 1.0 / T0 + (1.0 / BETA) * math.log(rth / R0)
    return 1.0 / inv_t - 273.15

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    wifi_connect()
    client = MQTTClient(
        client_id="esp32-bioreactor-poc",
        server="io.adafruit.com",
        port=1883,
        user=AIO_USER,
        password=AIO_KEY,
        keepalive=60,
    )
    client.connect()
    base = AIO_USER + "/feeds/"

    feeds = ("light", "temperature1", "temperature2")
    sums   = {f: 0.0 for f in feeds}
    counts = {f: 0   for f in feeds}
    last_pub = time.time()

    def accumulate(feed, value):
        if value is not None:
            sums[feed] += value
            counts[feed] += 1

    while True:
        # ---- sample ----
        try:
            accumulate("light", read_lux())
        except Exception as e:
            print("light read err:", e)

        accumulate("temperature1", adc_to_celsius(t1.read_u16()))
        accumulate("temperature2", adc_to_celsius(t2.read_u16()))

        # ---- publish on interval ----
        if time.time() - last_pub >= PUBLISH_INTERVAL:
            for feed in feeds:
                if counts[feed] == 0:
                    continue
                avg = sums[feed] / counts[feed]
                payload = "{:.2f}".format(avg)
                try:
                    client.publish(base + feed, payload)
                    print("pub", feed, "=", payload, "(n=%d)" % counts[feed])
                except Exception as e:
                    print("pub err:", e, "- reconnecting")
                    try:
                        client.connect()
                        client.publish(base + feed, payload)
                    except Exception:
                        wifi_connect()
                        client.connect()
                        client.publish(base + feed, payload)
                sums[feed] = 0.0
                counts[feed] = 0
            last_pub = time.time()

        time.sleep(SAMPLE_INTERVAL)

main()