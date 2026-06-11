import network, time, math
from machine import Pin, ADC, I2C
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASS, AIO_USER, AIO_KEY
from tcs34725 import TCS34725
import sensor_config as cfg

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
i2c = I2C(
    cfg.I2C_BUS,
    scl=Pin(cfg.I2C_SCL_PIN),
    sda=Pin(cfg.I2C_SDA_PIN),
    freq=cfg.I2C_FREQ,
)

light = TCS34725(i2c)
light.integration_time(cfg.LIGHT_INTEGRATION_TIME)
light.gain(cfg.LIGHT_GAIN)

# GPIO 36 and 39 are ADC1 channels. Required: ADC2 cannot be read while WiFi
# is active, so ADC1 is the only correct choice here.
t1 = ADC(Pin(cfg.THERMISTOR_1_PIN))
t1.atten(ADC.ATTN_11DB)

t2 = ADC(Pin(cfg.THERMISTOR_2_PIN))
t2.atten(ADC.ATTN_11DB)

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
    frac = raw / cfg.ADC_FULL

    if cfg.THERMISTOR_ON_LOW_SIDE:
        rth = cfg.R_FIXED * frac / (1.0 - frac)
    else:
        rth = cfg.R_FIXED * (1.0 - frac) / frac

    inv_t = 1.0 / cfg.T0 + (1.0 / cfg.BETA) * math.log(rth / cfg.R0)
    return 1.0 / inv_t - 273.15

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    wifi_connect()
    client = MQTTClient(
        client_id=cfg.MQTT_CLIENT_ID,
        server="io.adafruit.com",
        port=1883,
        user=AIO_USER,
        password=AIO_KEY,
        keepalive=60,
    )
    client.connect()
    base = AIO_USER + "/feeds/"

    feeds = cfg.FEEDS
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
            accumulate(cfg.FEED_LIGHT, read_lux())
        except Exception as e:
            print("light read err:", e)

        accumulate(cfg.FEED_TEMPERATURE_1, adc_to_celsius(t1.read_u16()))
        accumulate(cfg.FEED_TEMPERATURE_2, adc_to_celsius(t2.read_u16()))

        # ---- publish on interval ----
        if time.time() - last_pub >= cfg.PUBLISH_INTERVAL:
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

        time.sleep(cfg.SAMPLE_INTERVAL)

main()