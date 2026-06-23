from machine import Pin
from thermistor import Thermistor
from sensor_config import THERMISTOR_1_PIN, PIN36_ADC_LOOKUP
import utime

therm = Thermistor(pin_no=THERMISTOR_1_PIN, adc_lookup=PIN36_ADC_LOOKUP)

while True:
    temp = therm.read()
    print("T={:.2f}C".format(temp))
    utime.sleep(1)