from machine import I2C, Pin
import time

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
ADDR = 0x29

# Wake up: set ALS mode to active, gain x1
i2c.writeto_mem(ADDR, 0x80, bytes([0x01]))
time.sleep_ms(10)  # startup time

def read_als():
    # CH1 (IR) data: registers 0x88, 0x89
    # CH0 (visible+IR) data: registers 0x8A, 0x8B
    ch1_lo = i2c.readfrom_mem(ADDR, 0x88, 1)[0]
    ch1_hi = i2c.readfrom_mem(ADDR, 0x89, 1)[0]
    ch0_lo = i2c.readfrom_mem(ADDR, 0x8A, 1)[0]
    ch0_hi = i2c.readfrom_mem(ADDR, 0x8B, 1)[0]
    
    ch1 = (ch1_hi << 8) | ch1_lo  # IR
    ch0 = (ch0_hi << 8) | ch0_lo  # Visible + IR
    visible = ch0 - ch1            # human-visible approximation
    return ch0, ch1, visible

while True:
    ch0, ch1, vis = read_als()
    print(f"Visible+IR: {ch0}  IR: {ch1}  Visible: {vis}")
    time.sleep(1)