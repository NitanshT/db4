# wifitest.py
import network, time
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(reconnects=3)
wlan.connect("soheylwifi", "soheylso")   # type them literally, do not import config
for _ in range(20):
    if wlan.isconnected():
        print("OK", wlan.ifconfig()[0])
        break
    print("status", wlan.status())
    time.sleep(1)