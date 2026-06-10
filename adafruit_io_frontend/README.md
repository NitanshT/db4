# Mussels to Muscles Adafruit IO Frontend

Static GitHub Pages frontend for the ESP32 Adafruit IO feeds.

## Default feeds

The UI defaults match the current ESP32 publisher:

```text
temperature1
temperature2
light
```

Leave any feed field empty to hide it.

## Security

PLEASE do NOT hard-code your Adafruit IO key into `app.js` or `index.html`.
The browser form uses the key at runtime and can store it in localStorage only on that machine.
