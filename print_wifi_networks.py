import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
for net in wlan.scan():
    print(net[0])