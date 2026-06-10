from thermistor import Thermistor
import utime

print("I'm alive!\n")
utime.sleep_ms(2000)

#"The Christian shoemaker 
# does his Christian duty not by putting little crosses on the shoes, 
# but by making good shoes, because God is interested in good craftsmanship." - Martin Luther


therm1 = Thermistor(36, verbose=True)
therm2 = Thermistor(39, verbose=True)
sample_last_ms = 0
SAMPLE_INTERVAL = 1000

while True:
    if utime.ticks_diff(utime.ticks_ms(), sample_last_ms) >= SAMPLE_INTERVAL:
        temp1 = therm1.read()
        temp2 = therm2.read()
        print('Pin 36 Thermistor temperature: ' + str(temp1))
        print('Pin 39 Thermistor temperature: ' + str(temp2))

        sample_last_ms = utime.ticks_ms()