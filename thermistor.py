from machine import ADC, Pin
from time import sleep
import math

# ADC pin: use ADC1 pins, e.g. GPIO32-39
adc = ADC(Pin(36))

# ESP32 ADC settings
adc.atten(ADC.ATTN_11DB)      # allows reading up to approx 3.3V
adc.width(ADC.WIDTH_12BIT)    # raw range: 0-4095

# Voltage divider values
VCC = 3.3
R_FIXED = 10000.0   # 10k fixed resistor

# Thermistor parameters
R0 = 10000.0        # 10k at 25°C
T0 = 25.0 + 273.15  # Kelvin

# Assumed beta value.
# Replace this with the datasheet value if known.
BETA = 3950.0

def read_voltage(samples=32):
    total = sum(adc.read() for _ in range(samples))
    raw = total / samples
    voltage = raw / 4095 * VCC
    return raw, voltage

def calculate_resistance(voltage):
    # Wiring:
    # 3.3V -- thermistor -- ADC -- 10k resistor -- GND
    if voltage <= 0:
        return None

    r_thermistor = R_FIXED * voltage / (VCC - voltage)
    
    return r_thermistor

def calculate_temperature_celsius(r_thermistor):
    if r_thermistor <= 0:
        return None

    temp_k = 1 / ((1 / T0) + (1 / BETA) * math.log(r_thermistor / R0))
    temp_c = temp_k - 273.15
    return temp_c

while True:
    raw, voltage = read_voltage()
    resistance = calculate_resistance(voltage)

    if resistance is not None:
        temp_c = calculate_temperature_celsius(resistance)

        print("Raw:", raw)
        print("Voltage: {:.3f} V".format(voltage))
        print("Resistance: {:.1f} ohms".format(resistance))
        print("Temperature: {:.2f} °C".format(temp_c))
        print("-------------------------")

    sleep(1)