import network
import utime
from umqtt.simple import MQTTClient

from config import WIFI_SSID, WIFI_PASSWORD
from config import AIO_USERNAME, AIO_KEY, AIO_FEED_TEMP

# Import your course temperature functions
from thermistor_correct import init_temp_sensor, read_temp


# -----------------------------
# WiFi setup
# -----------------------------

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        while not wlan.isconnected():
            print(".", end="")
            utime.sleep(0.5)

    print("\nWiFi connected")
    print("IP address:", wlan.ifconfig()[0])
    return wlan


# -----------------------------
# Adafruit IO MQTT setup
# -----------------------------

MQTT_BROKER = "io.adafruit.com"
MQTT_PORT = 1883

CLIENT_ID = b"esp32-temperature-sensor"

TEMP_TOPIC = "{}/feeds/{}".format(
    AIO_USERNAME,
    AIO_FEED_TEMP
)

client = MQTTClient(
    client_id=CLIENT_ID,
    server=MQTT_BROKER,
    port=MQTT_PORT,
    user=AIO_USERNAME,
    password=AIO_KEY
)


def connect_mqtt():
    print("Connecting to Adafruit IO...")
    client.connect()
    print("Connected to Adafruit IO")


def publish_temperature(temp_c):
    payload = "{:.2f}".format(temp_c)
    print("Publishing:", payload, "to", TEMP_TOPIC)
    client.publish(TEMP_TOPIC, payload)


# -----------------------------
# Main program
# -----------------------------

connect_wifi()
connect_mqtt()

temp_sens = init_temp_sensor(32)

SAMPLE_INTERVAL_MS = 10000
last_sample_ms = 0

while True:
    now = utime.ticks_ms()

    if utime.ticks_diff(now, last_sample_ms) >= SAMPLE_INTERVAL_MS:
        try:
            temp = read_temp(temp_sens)
            print("Temperature:", temp, "°C")

            publish_temperature(temp)

        except Exception as e:
            print("Error:", e)

            try:
                client.disconnect()
            except:
                pass

            utime.sleep(2)
            connect_mqtt()

        last_sample_ms = now

    utime.sleep_ms(100)