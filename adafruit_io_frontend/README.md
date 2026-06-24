## Telemetry/status feeds

The frontend reads these numeric Adafruit IO feeds:

```text
temperature1
light
od-water
pwm-duty
elapsed-test-s
setpoint-temp
system-enable
test-number
test-duration-s
```

Do not use old/non-existing feeds such as `setpoint-active`, `relay-state`, `test-number-active`, `cooling-state`, `peltier-enable`, `auto-control`, or `manual-peltier`.

## Control feeds

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

## Experiment recording

`Start experiment` begins a browser-side recording session. It starts the local elapsed timer and clears any previous unsaved active recording.

While the experiment is running, the frontend records the numeric feed data it loads from Adafruit IO during that Start/Stop window. Recording is local to the browser and does not depend on the ESP32 knowing that the frontend is recording.

`Stop experiment` freezes the active recording, sets the stop time, and keeps the stopped session available for saving or export.

Each recording session stores:

```text
experimentName
notes
startedAt
stoppedAt
durationSeconds
settings/feed mapping
control values captured at start/stop
samples grouped by feed
```

## Data management and export

The data management panel is tied to experiment recording sessions.

It can:

```text
Save the stopped active session to localStorage
Export the stopped active session as CSV
Export the stopped active session as JSON
Export the latest saved session if no stopped active session exists
Export all saved sessions as JSON
Clear saved experiment sessions from localStorage
```

`Save snapshot locally` requires the experiment to be stopped first.

`Export latest CSV` and `Export latest JSON` use the stopped active session if one exists. Otherwise they use the latest saved session.

Saved data remains local to the browser unless you export it.

## Usage

1. Open the site.
2. Enter your Adafruit IO username and AIO key.
3. Click `Connect` to start loading Adafruit IO data.
4. Use `Remote controls` to write control values to Adafruit IO.
5. Click `Start experiment` when you want the browser to begin recording loaded data.
6. Click `Stop experiment` to freeze that recording session.
7. Use `Save snapshot locally` or the export buttons to keep or download the stopped session.

The ESP32 still publishes data to Adafruit IO. The frontend records the feed data that it loads during the selected experiment window.

## Security

Do not hard-code your Adafruit IO key into `app.js`, `index.html`, or any committed file. The browser form uses the key at runtime. Saving settings stores it only in `localStorage` on that machine.
