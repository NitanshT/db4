"""Thermistor driver for ESP32 (MicroPython).

NTC thermistor in a voltage divider, read via the ESP32 ADC with a
per-device lookup-table correction for the ADC's nonlinearity, converted
to temperature via the manufacturer R-T table (linear interpolation).

Usage in main.py:
    from thermistor import Thermistor
    from calibration import PIN_36_ADC_LOOKUP, PIN_39_ADC_LOOKUP

    therm1 = Thermistor(pin_no=36, adc_lookup=PIN_36_ADC_LOOKUP)
    therm2 = Thermistor(pin_no=39, adc_lookup=PIN_39_ADC_LOOKUP)
    temp_c = therm1.read()
"""

from machine import Pin, ADC

# Manufacturer R-T table: (temp_C, resistance_kOhm), resistance decreasing.
_RT_TABLE = [
    (-40, 277.2), (-39, 263.6), (-38, 250.1), (-37, 236.8), (-36, 224.0),
    (-35, 211.5), (-34, 199.6), (-33, 188.1), (-32, 177.3), (-31, 167.0),
    (-30, 157.2), (-29, 148.1), (-28, 139.4), (-27, 131.3), (-26, 123.7),
    (-25, 116.6), (-24, 110.0), (-23, 103.7), (-22, 97.9),  (-21, 92.50),
    (-20, 87.43), (-19, 82.79), (-18, 78.44), (-17, 74.36), (-16, 70.53),
    (-15, 66.92), (-14, 63.54), (-13, 60.34), (-12, 57.33), (-11, 54.50),
    (-10, 51.82), (-9, 49.28),  (-8, 46.89),  (-7, 44.62),  (-6, 42.48),
    (-5, 40.45),  (-4, 38.53),  (-3, 36.70),  (-2, 34.97),  (-1, 33.33),
    (0, 31.77),   (1, 30.25),   (2, 28.82),   (3, 27.45),   (4, 26.16),
    (5, 24.94),   (6, 23.77),   (7, 22.67),   (8, 21.62),   (9, 20.63),
    (10, 19.68),  (11, 18.78),  (12, 17.93),  (13, 17.12),  (14, 16.35),
    (15, 15.62),  (16, 14.93),  (17, 14.26),  (18, 13.63),  (19, 13.04),
    (20, 12.47),  (21, 11.92),  (22, 11.41),  (23, 10.91),  (24, 10.45),
    (25, 10.00),  (26, 9.575),  (27, 9.170),  (28, 8.784),  (29, 8.416),
    (30, 8.064),  (31, 7.730),  (32, 7.410),  (33, 7.106),  (34, 6.815),
    (35, 6.538),  (36, 6.273),  (37, 6.020),  (38, 5.778),  (39, 5.548),
    (40, 5.327),  (41, 5.117),  (42, 4.915),  (43, 4.723),  (44, 4.539),
    (45, 4.363),  (46, 4.195),  (47, 4.034),  (48, 3.880),  (49, 3.733),
    (50, 3.592),  (51, 3.457),  (52, 3.328),  (53, 3.204),  (54, 3.086),
    (55, 2.972),  (56, 2.863),  (57, 2.759),  (58, 2.659),  (59, 2.564),
    (60, 2.472),  (61, 2.384),  (62, 2.299),  (63, 2.218),  (64, 2.141),
    (65, 2.066),  (66, 1.994),  (67, 1.926),  (68, 1.860),  (69, 1.796),
    (70, 1.735),  (71, 1.677),  (72, 1.621),  (73, 1.567),  (74, 1.515),
    (75, 1.465),  (76, 1.417),  (77, 1.371),  (78, 1.326),  (79, 1.284),
    (80, 1.243),  (81, 1.203),  (82, 1.165),  (83, 1.128),  (84, 1.093),
    (85, 1.059),  (86, 1.027),  (87, 0.9955), (88, 0.9654), (89, 0.9363),
    (90, 0.9083), (91, 0.8812), (92, 0.8550), (93, 0.8297), (94, 0.8052),
    (95, 0.7816), (96, 0.7587), (97, 0.7366), (98, 0.7152), (99, 0.6945),
    (100, 0.6744),(101, 0.6558),(102, 0.6376),(103, 0.6199),(104, 0.6026),
    (105, 0.5858),(106, 0.5694),(107, 0.5535),(108, 0.5380),(109, 0.5229),
    (110, 0.5083),(111, 0.4941),(112, 0.4803),(113, 0.4669),(114, 0.4539),
    (115, 0.4412),(116, 0.4290),(117, 0.4171),(118, 0.4055),(119, 0.3944),
    (120, 0.3835),(121, 0.3730),(122, 0.3628),(123, 0.3530),(124, 0.3434),
    (125, 0.3341)]



def _resistance_to_temp(r_ohm):
    """Interpolate temperature from R-T table. r_ohm in ohms."""
    r_kohm = r_ohm / 1000.0
    # Clamp to table limits
    if r_kohm >= _RT_TABLE[0][1]:
        return float(_RT_TABLE[0][0])
    if r_kohm <= _RT_TABLE[-1][1]:
        return float(_RT_TABLE[-1][0])
    # Resistance decreases as index increases, so find bracketing pair
    for i in range(len(_RT_TABLE) - 1):
        t_lo, r_hi = _RT_TABLE[i]
        t_hi, r_lo = _RT_TABLE[i + 1]
        if r_lo <= r_kohm <= r_hi:
            frac = (r_kohm - r_hi) / (r_lo - r_hi)
            return t_lo + frac * (t_hi - t_lo)


class Thermistor:
    """NTC thermistor on an ESP32 ADC pin.

    Args:
        pin_no:      GPIO number the divider midpoint is wired to.
        adc_lookup:  1024-entry list from linearize.py for this specific pin.
        ser_res:     Measured series resistor value in ohms.
        num_samples: Readings averaged per measurement.
        verbose:     Print intermediate values (raw avg, voltage, resistance).
    """

    ADC_VMAX = 3.15

    def __init__(self, pin_no=36, adc_lookup=None, ser_res=10000,
                 num_samples=25, verbose=False):
        if adc_lookup is None:
            raise ValueError('adc_lookup is required — pass the lookup table for this pin.')
        self._lut = adc_lookup
        self.ser_res = ser_res
        self.num_samples = num_samples
        self.verbose = verbose

        self.adc = ADC(Pin(pin_no))
        self.adc.atten(ADC.ATTN_11DB)
        self.adc.width(ADC.WIDTH_10BIT)

    def read_raw(self):
        """Average of num_samples raw ADC codes (float, 0..1023)."""
        total = 0
        for _ in range(self.num_samples):
            total += self.adc.read()
        return total / self.num_samples

    def read_resistance(self):
        """Thermistor resistance in ohms."""
        raw_avg = self.read_raw()
        v = self._lut[round(raw_avg)]
        if v <= 0 or v >= self.ADC_VMAX:
            return None
        # Voltage divider: R_therm = R_fixed * V / (Vmax - V)
        resistance = self.ser_res * v / (self.ADC_VMAX - v)
        if self.verbose:
            print('raw_avg={:.1f}  V={:.4f}  R={:.1f} ohm'.format(raw_avg, v, resistance))
        return resistance

    def read(self):
        """Temperature in degrees Celsius via R-T table interpolation."""
        resistance = self.read_resistance()
        if resistance is None:
            return None
        return _resistance_to_temp(resistance)