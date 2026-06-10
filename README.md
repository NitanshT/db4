# **Mussels to Muscles** - 22400 Design-build 4: Autonomous devices for controlling and studying living systems

This repository contains the code for the **Mussels to Muscles** DB4 project: an autonomous monitoring system for studying a living mussel system using ESP32-based sensing and an Adafruit IO web interface.

## Repository structure

```text
db4/
├── adafruit/
│   ├── main.py
│   ├── publish.py
│   ├── sensor_config.py
│   ├── tcs34725.py
│   ├── thermistor.py
│   ├── thermistor_correct.py
│   └── tests/
│       ├── test_double_thermistor.py
│       ├── test_light_sensor.py
│       ├── test_lightsensor_module.py
│       └── test_wifi_scan.py
│
├── adafruit_io_frontend/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── assets/
│
├── .gitignore
└── README.md
```

## ESP32 firmware

The ESP32 firmware is located in:

```text
adafruit/
```

The main production files are:

* `main.py` - ESP32 boot entry point
* `publish.py` - sensor reading and Adafruit IO publishing loop
* `sensor_config.py` - feed names, pin numbers, and sampling settings
* `tcs34725.py` - light sensor driver
* `thermistor.py` / `thermistor_correct.py` - thermistor reading code

Private credentials are stored locally in:

```text
adafruit/config.py
```

This file must NOT be committed to Git.

## Adafruit IO feeds

The current frontend and ESP32 publisher expect these feed keys:

```text
temperature1
temperature2
light
```

The web dashboard will show errors until the ESP32 has successfully published data to these feeds.

## Frontend dashboard

The static frontend is located in:

```text
adafruit_io_frontend/
```

## Test scripts

Hardware test scripts are stored in:

```text
adafruit/tests/
```

These are used for checking individual components before running the full system.

## Security note

PLEASE do NOT commit:

```text
adafruit/config.py
```

This file contains WiFi credentials and the Adafruit IO key. The root `.gitignore` should include:

```gitignore
adafruit/config.py
```
