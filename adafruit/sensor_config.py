# Central hardware and timing configuration for the ESP32 sensor system.
#"Scientists investigate that which alrady is; 
# engineers create that which has never been" - Albert Einstein

# ---------------------------------------------------------------------------
# TIMING
# ---------------------------------------------------------------------------

SAMPLE_INTERVAL = 2       # seconds between individual measurements
PUBLISH_INTERVAL = 3     # seconds between Adafruit IO publishes

# ---------------------------------------------------------------------------
# ADAFRUIT IO
# ---------------------------------------------------------------------------

MQTT_CLIENT_ID = "esp32-bioreactor-poc"

FEED_LIGHT = "light"
FEED_TEMPERATURE_1 = "temperature1"
FEED_TEMPERATURE_2 = "temperature2"

FEEDS = (
    FEED_LIGHT,
    FEED_TEMPERATURE_1,
    FEED_TEMPERATURE_2,
)

# ---------------------------------------------------------------------------
# I2C LIGHT SENSOR: TCS34725
# ---------------------------------------------------------------------------

I2C_BUS = 0
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
I2C_FREQ = 100000

LIGHT_INTEGRATION_TIME = 100
LIGHT_GAIN = 4

# ---------------------------------------------------------------------------
# THERMISTORS
# ---------------------------------------------------------------------------

THERMISTOR_1_PIN = 36
THERMISTOR_2_PIN = 39

# GPIO36 and GPIO39 are ADC1 pins.
# ADC1 is preferred because ESP32 ADC2 conflicts with WiFi.

R_FIXED = 10000.0
R0 = 10000.0
BETA = 3950.0
T0 = 298.15

# True  = 3V3 -- R_FIXED -- [ADC node] -- thermistor -- GND
# False = 3V3 -- thermistor -- [ADC node] -- R_FIXED -- GND
THERMISTOR_ON_LOW_SIDE = True

ADC_FULL = 65535.0