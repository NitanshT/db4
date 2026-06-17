# Central hardware, timing and Adafruit IO feed configuration for the ESP32 bioreactor system.

# ---------------------------------------------------------------------------
# TIMING
# ---------------------------------------------------------------------------

SAMPLE_INTERVAL = 2        # seconds between individual sensor measurements
PUBLISH_INTERVAL = 10      # seconds between Adafruit IO publishes; increase if throttled

# ---------------------------------------------------------------------------
# ADAFRUIT IO
# ---------------------------------------------------------------------------

MQTT_CLIENT_ID = "esp32-bioreactor-poc"

# Telemetry feeds: ESP32 -> Adafruit IO
FEED_LIGHT = "light"
FEED_OD_WATER = "od-water"
FEED_TEMPERATURE_1 = "temperature1"      # Mussels
FEED_TEMPERATURE_2 = "temperature2"      # Algae
FEED_RELAY_STATE = "relay-state"
FEED_COOLING_STATE = "cooling-state"
FEED_SETPOINT_ACTIVE = "setpoint-active"
FEED_TEST_NUMBER_ACTIVE = "test-number-active"
FEED_ELAPSED_TEST_S = "elapsed-test-s"

PUBLISH_FEEDS = (
    FEED_LIGHT,
    FEED_OD_WATER,
    FEED_TEMPERATURE_1,
    FEED_TEMPERATURE_2,
    FEED_RELAY_STATE,
    FEED_COOLING_STATE,
    FEED_SETPOINT_ACTIVE,
    FEED_TEST_NUMBER_ACTIVE,
    FEED_ELAPSED_TEST_S,
)

# Control feeds: Adafruit IO -> ESP32
FEED_SETPOINT_TEMP = "setpoint-temp"
FEED_PELTIER_ENABLE = "peltier-enable"
FEED_AUTO_CONTROL = "auto-control"
FEED_MANUAL_PELTIER = "manual-peltier"
FEED_TEST_NUMBER = "test-number"
FEED_TEST_DURATION_S = "test-duration-s"

CONTROL_FEEDS = (
    FEED_SETPOINT_TEMP,
    FEED_PELTIER_ENABLE,
    FEED_AUTO_CONTROL,
    FEED_MANUAL_PELTIER,
    FEED_TEST_NUMBER,
    FEED_TEST_DURATION_S,
)

# ---------------------------------------------------------------------------
# DEFAULT REMOTE-CONTROL STATE
# ---------------------------------------------------------------------------

DEFAULT_SETPOINT_TEMP = 18.0
TEMP_HYSTERESIS = 0.5       # relay deadband in deg C; prevents fast relay chatter
DEFAULT_AUTO_CONTROL = True
DEFAULT_PELTIER_ENABLE = False
DEFAULT_MANUAL_PELTIER = False
DEFAULT_TEST_NUMBER = 1
DEFAULT_TEST_DURATION_S = 600

# ---------------------------------------------------------------------------
# RELAY / PELTIER CONTROL
# ---------------------------------------------------------------------------

RELAY_PIN = 26
RELAY_ACTIVE_LOW = True     # common 5V relay modules turn ON when GPIO is LOW

# ---------------------------------------------------------------------------
# I2C: OLED + TCS34725
# ---------------------------------------------------------------------------

I2C_BUS = 0
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
I2C_FREQ = 100000

LIGHT_INTEGRATION_TIME = 100
LIGHT_GAIN = 4

# Blank-water calibration value for OD conversion.
# Replace this after measuring clear/reference water with your final optical setup.
OD_BLANK_LUX = 100.0

# ---------------------------------------------------------------------------
# THERMISTORS
# ---------------------------------------------------------------------------

THERMISTOR_1_PIN = 36
THERMISTOR_2_PIN = 39

R_FIXED = 10000.0
R0 = 10000.0
BETA = 3950.0
T0 = 298.15
THERMISTOR_ON_LOW_SIDE = True
ADC_FULL = 65535.0
