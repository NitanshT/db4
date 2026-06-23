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

The frontend writes only these control values to Adafruit IO:

```text
setpoint-temp
system-enable
test-number
test-duration-s
```

`setpoint-temp` is the PI temperature reference point. The ESP32 should update the PI controller setpoint from this feed.

`system-enable` is the full remote system enable/disable control:

```text
1 = system enabled / PI control allowed to run
0 = system disabled / actuators forced OFF or duty = 0
```

The ESP32 must subscribe to these feeds over MQTT.

## Usage

1. Open the site.
2. Enter your Adafruit IO username and AIO key.
3. Click **Connect** to load data.
4. Use **Remote controls** to write control values to Adafruit IO.
5. The ESP32 reads those control feeds and updates the PI setpoint and system enable state.

## Security

Do NOT hard-code your Adafruit IO key into `app.js`, `index.html`, or any committed file.
The browser form uses the key at runtime. Saving settings stores it only in `localStorage` on that machine.
