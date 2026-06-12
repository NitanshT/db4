import time
import ustruct

# LTR-329ALS-01 register map (no command bit; addresses are used directly,
# unlike the TCS34725 which ORs in 0x80)
_REG_ALS_CONTR     = const(0x80)
_REG_ALS_MEAS_RATE = const(0x85)
_REG_PART_ID       = const(0x86)
_REG_MANUFAC_ID    = const(0x87)
_REG_ALS_DATA      = const(0x88)  # CH1 low, CH1 high, CH0 low, CH0 high
_REG_ALS_STATUS    = const(0x8C)

# ALS_CONTR bits
_CONTR_ACTIVE = const(0x01)
_CONTR_RESET  = const(0x02)

# Valid settings -> register bit patterns
_GAINS = {1: 0b000, 2: 0b001, 4: 0b010, 8: 0b011, 48: 0b110, 96: 0b111}
_INT_TIMES = {100: 0b000, 50: 0b001, 200: 0b010, 400: 0b011,
              150: 0b100, 250: 0b101, 300: 0b110, 350: 0b111}  # ms
_MEAS_RATES = {50: 0b000, 100: 0b001, 200: 0b010,
               500: 0b011, 1000: 0b100, 2000: 0b101}  # ms

_PART_ID = const(0xA0)
_MANUFAC_ID = const(0x05)


class LTR329:
    def __init__(self, i2c, address=0x29, gain=1,
                 integration_time=100, measurement_rate=500):
        self.i2c = i2c
        self.address = address
        self._active = False

        if self._register8(_REG_PART_ID) != _PART_ID:
            raise RuntimeError("wrong part id")
        if self._register8(_REG_MANUFAC_ID) != _MANUFAC_ID:
            raise RuntimeError("wrong manufacturer id")

        self._gain = gain
        self._int_time = integration_time
        self.gain(gain)
        self.measurement(integration_time, measurement_rate)

    # -- low level ----------------------------------------------------

    def _register8(self, register, value=None):
        if value is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        self.i2c.writeto_mem(self.address, register, ustruct.pack('<B', value))

    # -- configuration ------------------------------------------------

    def active(self, value=None):
        if value is None:
            return self._active
        value = bool(value)
        if self._active == value:
            return
        self._active = value
        contr = self._register8(_REG_ALS_CONTR)
        gain_bits = contr & 0b00011100
        if value:
            self._register8(_REG_ALS_CONTR, gain_bits | _CONTR_ACTIVE)
            time.sleep_ms(10)   # standby -> active wakeup
        else:
            self._register8(_REG_ALS_CONTR, gain_bits)

    def gain(self, value=None):
        if value is None:
            return self._gain
        if value not in _GAINS:
            raise ValueError("gain must be 1, 2, 4, 8, 48 or 96")
        self._gain = value
        contr = _GAINS[value] << 2
        if self._active:
            contr |= _CONTR_ACTIVE
        self._register8(_REG_ALS_CONTR, contr)

    def measurement(self, integration_time=None, rate=None):
        if integration_time is None and rate is None:
            reg = self._register8(_REG_ALS_MEAS_RATE)
            it = [k for k, v in _INT_TIMES.items() if v == (reg >> 3) & 0x07][0]
            mr = [k for k, v in _MEAS_RATES.items() if v == reg & 0x07][0]
            return it, mr
        if integration_time is not None:
            if integration_time not in _INT_TIMES:
                raise ValueError("invalid integration time")
            self._int_time = integration_time
        if rate is None:
            rate = 500
        if rate not in _MEAS_RATES:
            raise ValueError("invalid measurement rate")
        if rate < self._int_time:
            raise ValueError("rate must be >= integration time")
        self._register8(_REG_ALS_MEAS_RATE,
                        (_INT_TIMES[self._int_time] << 3) | _MEAS_RATES[rate])

    # -- data ---------------------------------------------------------

    def _status(self):
        return self._register8(_REG_ALS_STATUS)

    def _new_data(self):
        return bool(self._status() & 0x04)

    def read(self, raw=False):
        was_active = self.active()
        self.active(True)
        while not self._new_data():
            time.sleep_ms(self._int_time // 4)
        # Burst-read all 4 bytes; CH1 must be read before CH0 and the
        # datasheet requires reading low byte before high byte (data lock)
        data = self.i2c.readfrom_mem(self.address, _REG_ALS_DATA, 4)
        ch1, ch0 = ustruct.unpack('<HH', data)
        if self._status() & 0x80:
            raise RuntimeError("data invalid (sensor saturated?)")
        self.active(was_active)
        if raw:
            return ch0, ch1   # ch0 = visible + IR, ch1 = IR
        return self._lux(ch0, ch1)

    def _lux(self, ch0, ch1):
        # Appendix A of the LTR-329ALS-01 datasheet
        if ch0 + ch1 == 0:
            return 0.0
        ratio = ch1 / (ch0 + ch1)
        als_int = self._int_time / 100  # in units of 100 ms
        if ratio < 0.45:
            lux = 1.7743 * ch0 + 1.1059 * ch1
        elif ratio < 0.64:
            lux = 4.2785 * ch0 - 1.9548 * ch1
        elif ratio < 0.85:
            lux = 0.5926 * ch0 + 0.1185 * ch1
        else:
            return 0.0
        return lux / self._gain / als_int