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

A saved/exported snapshot contains:

```text
Experiment name
Experiment notes/conditions
Adafruit username and feed mapping
Remote-control parameter values
Loaded telemetry results
Timestamps and units
```

Data is stored in browser `localStorage`, so it remains local to that browser/machine.
CSV and JSON exports are standard downloadable files.

## Usage

1. Open the site.
2. Enter your Adafruit IO username and AIO key.
3. Click **Connect** to load data.
4. Use **Remote controls** to write control values to Adafruit IO.
5. Use **Data management and export** to save or export results.
6. The ESP32 reads the control feeds and updates the PI setpoint and system enable state.

## Security

Do NOT hard-code your Adafruit IO key into `app.js`, `index.html`, or any committed file.
The browser form uses the key at runtime. Saving settings stores it only in `localStorage` on that machine.
