import network, time, math
from machine import Pin, ADC, I2C
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASS, AIO_USER, AIO_KEY
from tcs34725 import TCS34725
import adafruit.sensor_config as cfg

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
print("i2c devices:", [hex(x) for x in i2c.scan()])

light = TCS34725(i2c)
light.integration_time(cfg.LIGHT_INTEGRATION_TIME)
light.gain(cfg.LIGHT_GAIN)

t1 = ADC(Pin(cfg.THERMISTOR_1_PIN))
t1.atten(ADC.ATTN_11DB)

t2 = ADC(Pin(cfg.THERMISTOR_2_PIN))
t2.atten(ADC.ATTN_11DB)

relay = Pin(cfg.RELAY_PIN, Pin.OUT)
relay_state = False

def set_relay(on):
    global relay_state
    relay_state = bool(on)
    if cfg.RELAY_ACTIVE_LOW:
        relay.value(0 if relay_state else 1)
    else:
        relay.value(1 if relay_state else 0)

set_relay(False)

# ---------------------------------------------------------------------------
# REMOTE-CONTROL STATE
# ---------------------------------------------------------------------------

state = {
    "setpoint_temp": cfg.DEFAULT_SETPOINT_TEMP,
    "peltier_enable": cfg.DEFAULT_PELTIER_ENABLE,
    "auto_control": cfg.DEFAULT_AUTO_CONTROL,
    "manual_peltier": cfg.DEFAULT_MANUAL_PELTIER,
    "test_number": cfg.DEFAULT_TEST_NUMBER,
    "test_duration_s": cfg.DEFAULT_TEST_DURATION_S,
}

test_start_ms = time.ticks_ms()

# ---------------------------------------------------------------------------
# SENSOR FUNCTIONS
# ---------------------------------------------------------------------------

def read_lux():
    r, g, b, c = light.read(raw=True)
    y = -0.32466 * r + 1.57837 * g + -0.73191 * b
    return max(0.0, y)

def lux_to_od(lux):
    if lux is None or lux <= 0 or cfg.OD_BLANK_LUX <= 0:
        return None
    return max(0.0, math.log10(cfg.OD_BLANK_LUX / lux))

def adc_to_celsius(raw):
    if raw < 100 or raw > 65435:
        return None
    frac = raw / cfg.ADC_FULL
    if frac <= 0.0 or frac >= 1.0:
        return None

    if cfg.THERMISTOR_ON_LOW_SIDE:
        rth = cfg.R_FIXED * frac / (1.0 - frac)
    else:
        rth = cfg.R_FIXED * (1.0 - frac) / frac

    inv_t = 1.0 / cfg.T0 + (1.0 / cfg.BETA) * math.log(rth / cfg.R0)
    return 1.0 / inv_t - 273.15

# ---------------------------------------------------------------------------
# MQTT CONTROL CALLBACK
# ---------------------------------------------------------------------------

def as_text(x):
    if isinstance(x, bytes):
        return x.decode().strip()
    return str(x).strip()

def as_bool(payload):
    value = as_text(payload).lower()
    return value in ("1", "on", "true", "yes", "enable", "enabled")

def on_message(topic, msg):
    global test_start_ms
    topic_s = as_text(topic)
    msg_s = as_text(msg)
    feed = topic_s.split("/")[-1]

    print("rx", feed, "=", msg_s)

    try:
        if feed == cfg.FEED_SETPOINT_TEMP:
            value = float(msg_s)
            # Safety clamp for the living system.
            state["setpoint_temp"] = max(10.0, min(30.0, value))

        elif feed == cfg.FEED_PELTIER_ENABLE:
            state["peltier_enable"] = as_bool(msg_s)
            if not state["peltier_enable"]:
                set_relay(False)

        elif feed == cfg.FEED_AUTO_CONTROL:
            state["auto_control"] = as_bool(msg_s)

        elif feed == cfg.FEED_MANUAL_PELTIER:
            state["manual_peltier"] = as_bool(msg_s)

        elif feed == cfg.FEED_TEST_NUMBER:
            state["test_number"] = max(1, int(float(msg_s)))
            test_start_ms = time.ticks_ms()

        elif feed == cfg.FEED_TEST_DURATION_S:
            state["test_duration_s"] = max(10, int(float(msg_s)))

    except Exception as e:
        print("bad control value for", feed, ":", msg_s, e)

# ---------------------------------------------------------------------------
# CONTROL LAW
# ---------------------------------------------------------------------------

def update_peltier_control(temp_mussels):
    if not state["peltier_enable"]:
        set_relay(False)
        return

    if not state["auto_control"]:
        set_relay(state["manual_peltier"])
        return

    if temp_mussels is None:
        set_relay(False)
        return

    setpoint = state["setpoint_temp"]
    h = cfg.TEMP_HYSTERESIS / 2.0

    # Cooling control: relay ON when too warm, OFF when below the lower band.
    if temp_mussels > setpoint + h:
        set_relay(True)
    elif temp_mussels < setpoint - h:
        set_relay(False)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def publish_value(client, base, feed, value):
    if value is None:
        return
    if isinstance(value, float):
        payload = "{:.2f}".format(value)
    else:
        payload = str(value)
    client.publish(base + feed, payload)
    print("pub", feed, "=", payload)

def connect_mqtt():
    client = MQTTClient(
        client_id=cfg.MQTT_CLIENT_ID,
        server="io.adafruit.com",
        port=1883,
        user=AIO_USER,
        password=AIO_KEY,
        keepalive=60,
    )
    client.set_callback(on_message)
    client.connect()
    base = AIO_USER + "/feeds/"
    for feed in cfg.CONTROL_FEEDS:
        client.subscribe(base + feed)
        print("sub", feed)
    return client, base

def main():
    wifi_connect()
    client, base = connect_mqtt()

    sums = {f: 0.0 for f in cfg.PUBLISH_FEEDS}
    counts = {f: 0 for f in cfg.PUBLISH_FEEDS}
    last_pub = time.time()

    def accumulate(feed, value):
        if value is not None:
            sums[feed] += value
            counts[feed] += 1

    while True:
        try:
            client.check_msg()
        except Exception as e:
            print("mqtt check err:", e, "- reconnecting")
            try:
                client.disconnect()
            except Exception:
                pass
            wifi_connect()
            client, base = connect_mqtt()

        lux = None
        try:
            lux = read_lux()
            accumulate(cfg.FEED_LIGHT, lux)
            accumulate(cfg.FEED_OD_WATER, lux_to_od(lux))
        except Exception as e:
            print("light read err:", e)

        temp1 = adc_to_celsius(t1.read_u16())
        temp2 = adc_to_celsius(t2.read_u16())

        accumulate(cfg.FEED_TEMPERATURE_1, temp1)
        accumulate(cfg.FEED_TEMPERATURE_2, temp2)

        update_peltier_control(temp1)

        elapsed_s = time.ticks_diff(time.ticks_ms(), test_start_ms) // 1000
        if elapsed_s >= state["test_duration_s"]:
            state["test_number"] += 1
            test_start_ms = time.ticks_ms()
            elapsed_s = 0

        if time.time() - last_pub >= cfg.PUBLISH_INTERVAL:
            try:
                for feed in cfg.PUBLISH_FEEDS:
                    if counts[feed] > 0:
                        avg = sums[feed] / counts[feed]
                        publish_value(client, base, feed, avg)
                        sums[feed] = 0.0
                        counts[feed] = 0

                publish_value(client, base, cfg.FEED_RELAY_STATE, 1 if relay_state else 0)
                publish_value(client, base, cfg.FEED_COOLING_STATE, "ON" if relay_state else "OFF")
                publish_value(client, base, cfg.FEED_SETPOINT_ACTIVE, state["setpoint_temp"])
                publish_value(client, base, cfg.FEED_TEST_NUMBER_ACTIVE, state["test_number"])
                publish_value(client, base, cfg.FEED_ELAPSED_TEST_S, elapsed_s)

            except Exception as e:
                print("publish err:", e, "- reconnecting")
                try:
                    client.disconnect()
                except Exception:
                    pass
                wifi_connect()
                client, base = connect_mqtt()

            last_pub = time.time()

        time.sleep(cfg.SAMPLE_INTERVAL)

main()
