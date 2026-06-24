## Telemetry feeds

The UI defaults match the ESP32 dashboard publisher:

```text
temperature1
light
od-water
setpoint-active
relay-state
cooling-state
pwm-duty
test-number-active
elapsed-test-s
```

## Remote-control feeds

The frontend writes these control values to Adafruit IO:

```text
setpoint-temp
system-enable
test-number
test-duration-s
system-reset
```

`setpoint-temp` is the PI temperature reference point.

`system-enable` is the software ON/OFF control:

```text
1 = system enabled / self-test, prime, PI loop and pump logic allowed
0 = system disabled / actuators forced OFF while MQTT keeps listening
```

`system-reset` sends a reset command to the ESP32.

The removed legacy controls are not used by the current ESP32 script:

```text
peltier-enable
auto-control
manual-peltier
```

## Data management and export

The frontend includes a local data management panel for experiment documentation.

It can:

```text
Save a local experiment snapshot
Export the latest loaded results as CSV
Export the latest loaded results as JSON
Export all locally stored snapshots as JSON
Clear locally stored snapshots
```

Data is stored in browser `localStorage`, so it remains local to that browser/machine. CSV and JSON exports are standard downloadable files.

## Usage

1. Open the site.
2. Enter your Adafruit IO username and AIO key.
3. Click **Connect** to load data.
4. Use **Remote controls** to write control values to Adafruit IO.
5. Keep **System enable** OFF while sensors are disconnected.
6. Use **Data management and export** to save or export results.

## Security

Do NOT hard-code your Adafruit IO key into `app.js`, `index.html`, or any committed file. The browser form uses the key at runtime. Saving settings stores it only in `localStorage` on that machine.
