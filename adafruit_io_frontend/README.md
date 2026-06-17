## Telemetry feeds

The UI defaults match the ESP32 dashboard publisher:

```text
temperature1
temperature2
light
od-water
setpoint-active
relay-state
test-number-active
elapsed-test-s
```

Leave any feed field empty to hide it from the charts/cards.

## Remote-control feeds

The frontend can write control values to these Adafruit IO feeds:

```text
setpoint-temp
peltier-enable
auto-control
manual-peltier
test-number
test-duration-s
```

The ESP32 must subscribe to these feeds over MQTT. The matching ESP32 files are `publish_dashboard.py` and `sensor_config_dashboard.py`.

## Usage

1. Open the site.
2. Enter your Adafruit IO username and AIO key.
3. Click **Connect** to load data.
4. Use **Remote controls** to write control values to Adafruit IO.
5. The ESP32 reads those control feeds and updates the relay/Peltier control loop.

## Security

Do NOT hard-code your Adafruit IO key into `app.js`, `index.html`, or any committed file.
The browser form uses the key at runtime. Saving settings stores it only in `localStorage` on that machine.
