"""
main.py - ESP32 bioreactor experiment controller (MicroPython).

Boot order is Wi-Fi first, then MQTT, then the heavier sensor/display modules.
This keeps the Wi-Fi/MQTT heap allocations ahead of the large lookup-table imports.
Remote feeds: setpoint-temp, system-enable, test-number, test-duration-s, system-reset.
"""

import network

_wlan = network.WLAN(network.STA_IF)
_wlan.active(True)

import time
import gc
from machine import reset
from config import WIFI_SSID, WIFI_PASS, AIO_USER, AIO_KEY


DEFAULT_SETPOINT_C = 17.0
PUMP_PIN = 32

CONTROL_PERIOD_MS = 1000
TELEMETRY_PERIOD_S = 5
STATUS_PERIOD_S = 10
PUMP_INTERVAL_S = 15 * 60
PRIME_PUMP_S = 3
EXP_PUMP_S = 1
CH0_BURST_S = 5

MIN_VALID_TEMP_C = 5
MAX_VALID_TEMP_C = 35
MAX_CONSEC_ERRORS = 5
RECONNECT_BACKOFF_S = 30
LOG_FLUSH_EVERY = 10

TEMP_LOG_FILE = "temp_pwm_log.csv"
LIGHT_LOG_FILE = "light_log.csv"

FEED_SETPOINT_TEMP = "setpoint-temp"
FEED_SYSTEM_ENABLE = "system-enable"
FEED_TEST_NUMBER = "test-number"
FEED_TEST_DURATION_S = "test-duration-s"
FEED_SYSTEM_RESET = "system-reset"

# The Adafruit dashboard uses the same feeds for controls and displayed values.
# Do not publish to non-existing "*-active" feeds unless you create them.
PUBLISH_EXTRA_STATUS_FEEDS = False


disp = None
btn = None
math = None
utime = None
Pin = None
PWM = None
I2C = None
LTR329 = None
Thermistor = None
MQTTClient = None
cfg = None

OLED_AVAILABLE = False
BUTTON_AVAILABLE = False

pwm = None
pump = None
therm = None
light = None
client = None
base = None
_i2c = None
_integral = 0.0
_pub_pause_until_ms = None
_last_status_publish_ms = None
_last_telemetry_publish_ms = None
_last_cooling_state = None
_last_fault = ""

state = {
    "setpoint_temp": DEFAULT_SETPOINT_C,
    "system_enabled": False,
    "test_number": 1,
    "test_duration_s": 600,
    "test_start_s": time.time(),
    "run_needs_prime": True,
}


def clamp(value, low, high):
    return max(low, min(high, value))


def as_text(value):
    if isinstance(value, bytes):
        return value.decode().strip()
    return str(value).strip()


def as_bool(value):
    return as_text(value).lower() in (
        "1", "on", "true", "yes", "enable", "enabled"
    )


def elapsed_test_s():
    return max(0, int(time.time() - state["test_start_s"]))


def screen(*lines):
    global OLED_AVAILABLE
    clean = [str(line) for line in lines if line is not None]
    print("[SCREEN]", " | ".join(clean[:6]))
    if not OLED_AVAILABLE or disp is None:
        return
    try:
        disp._oled.fill(0)
        for idx, line in enumerate(clean[:6]):
            disp._oled.text(line[:16], 0, idx * 10)
        disp._oled.show()
    except Exception as exc:
        OLED_AVAILABLE = False
        print("oled write disabled:", exc)


def wifi_connect():
    wlan = _wlan

    print("SSID repr:", repr(WIFI_SSID))
    print("PASS len:", len(WIFI_PASS))

    if not wlan.active():
        wlan.active(True)
        time.sleep(0.5)

    try:
        wlan.config(reconnects=5)
    except Exception:
        pass

    if wlan.isconnected():
        print("wifi already ok", wlan.ifconfig())
        return wlan

    for cycle in range(1, 4):
        screen("WiFi cycle {}".format(cycle), WIFI_SSID)
        try:
            wlan.disconnect()
            time.sleep(0.5)
        except Exception:
            pass

        gc.collect()
        print("wifi status before connect:", wlan.status())
        wlan.connect(WIFI_SSID, WIFI_PASS)

        for second in range(20):
            status = wlan.status()
            print("wifi cycle", cycle, "t", second, "status", status)
            if wlan.isconnected():
                print("wifi ok", wlan.ifconfig())
                return wlan
            time.sleep(1)

    final_status = wlan.status()
    screen("WiFi FAILED", "status {}".format(final_status))
    raise RuntimeError("wifi failed: {}".format(final_status))


def load_mqtt_module():
    """Load MQTT before the heavy sensor/display modules.

    This keeps socket/MQTT heap allocation close to the early Wi-Fi allocation.
    """
    global MQTTClient
    if MQTTClient is not None:
        return
    gc.collect()
    from umqtt.simple import MQTTClient as _MQTTClient
    MQTTClient = _MQTTClient
    gc.collect()
    print("mqtt module loaded")


def load_runtime_modules():
    global math, utime, Pin, PWM, I2C
    global LTR329, Thermistor, MQTTClient, cfg
    global disp, btn, OLED_AVAILABLE, BUTTON_AVAILABLE

    import math as _math
    import utime as _utime
    from machine import Pin as _Pin, PWM as _PWM, I2C as _I2C
    from LTR329 import LTR329 as _LTR329
    from thermistor import Thermistor as _Thermistor
    import sensor_config as _cfg

    math = _math
    utime = _utime
    Pin = _Pin
    PWM = _PWM
    I2C = _I2C
    LTR329 = _LTR329
    Thermistor = _Thermistor
    cfg = _cfg

    try:
        import oled_display as _disp
        disp = _disp
        OLED_AVAILABLE = True
        print("oled import ok")
    except Exception as exc:
        disp = None
        OLED_AVAILABLE = False
        print("oled unavailable:", exc)

    try:
        import button as _btn
        btn = _btn
        BUTTON_AVAILABLE = True
        print("button import ok")
    except Exception as exc:
        btn = None
        BUTTON_AVAILABLE = False
        print("button unavailable:", exc)

    # Free unused large ADC lookup table if present. The current hardware path uses
    # only THERMISTOR_1_PIN / PIN36_ADC_LOOKUP. Keeping PIN39_ADC_LOOKUP in RAM can
    # make ESP32 ADC initialisation fail with ESP_ERR_NO_MEM.
    try:
        if hasattr(cfg, "PIN39_ADC_LOOKUP"):
            del cfg.PIN39_ADC_LOOKUP
            gc.collect()
            print("freed unused PIN39_ADC_LOOKUP")
    except Exception as exc:
        print("could not free PIN39_ADC_LOOKUP:", exc)

    try:
        import micropython
        print("mem free after runtime modules:", gc.mem_free())
    except Exception:
        pass

    print("runtime modules loaded")


def get_i2c():
    global _i2c
    if _i2c is not None:
        return _i2c

    if OLED_AVAILABLE and disp is not None and hasattr(disp, "_i2c"):
        _i2c = disp._i2c
    else:
        bus = getattr(cfg, "I2C_BUS", 0)
        scl = getattr(cfg, "I2C_SCL_PIN", 22)
        sda = getattr(cfg, "I2C_SDA_PIN", 21)
        freq = getattr(cfg, "I2C_FREQ", 100000)
        _i2c = I2C(bus, scl=Pin(scl), sda=Pin(sda), freq=freq)

    try:
        print("i2c scan:", [hex(addr) for addr in _i2c.scan()])
    except Exception as exc:
        print("i2c scan err:", exc)
    return _i2c


def button_pressed():
    if not BUTTON_AVAILABLE or btn is None:
        return False
    try:
        return btn.check_for_press()
    except Exception as exc:
        print("button err:", exc)
        return False


def force_outputs_off():
    try:
        if pwm is not None:
            pwm.duty(0)
    except Exception:
        pass
    try:
        if pump is not None:
            pump.value(0)
    except Exception:
        pass


def feed_name(name, fallback):
    return getattr(cfg, name, fallback)


def control_feeds():
    return (
        FEED_SETPOINT_TEMP,
        FEED_SYSTEM_ENABLE,
        FEED_TEST_NUMBER,
        FEED_TEST_DURATION_S,
        FEED_SYSTEM_RESET,
    )


def mqtt_connect():
    global client, base, _pub_pause_until_ms

    if MQTTClient is None:
        load_mqtt_module()

    base = AIO_USER + "/feeds/"
    client_id = getattr(cfg, "MQTT_CLIENT_ID", None) or "esp32-bioreactor-poc"
    last_exc = None

    # Wi-Fi may report connected before DNS/TCP is ready. Give it a short settle time.
    time.sleep(2)

    for attempt in range(1, 6):
        try:
            wifi_connect()
            gc.collect()
            print("mqtt connect attempt", attempt)

            candidate = MQTTClient(
                client_id=client_id,
                server="io.adafruit.com",
                port=1883,
                user=AIO_USER,
                password=AIO_KEY,
                keepalive=60,
            )
            candidate.set_callback(on_message)
            candidate.connect()
            try:
                candidate.sock.settimeout(5)
                print("mqtt socket timeout set to 5s")
            except Exception as exc:
                print("mqtt socket timeout unavailable:", exc)
            client = candidate

            for feed in control_feeds():
                try:
                    client.subscribe(base + feed)
                    print("sub", feed)
                except Exception as exc:
                    print("sub err", feed, exc)

            _pub_pause_until_ms = None
            print("mqtt connected")
            return client

        except Exception as exc:
            last_exc = exc
            print("mqtt connect err attempt", attempt, exc)
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass
            client = None
            gc.collect()
            time.sleep(3)

    raise last_exc


def _try_reconnect():
    global client
    try:
        wifi_connect()
        try:
            if client is not None:
                client.disconnect()
        except Exception:
            pass
        mqtt_connect()
        return True
    except Exception as exc:
        print("reconnect failed:", exc)
        return False


def publish(feed, value):
    global _pub_pause_until_ms
    if client is None or base is None or value is None:
        return False

    if _pub_pause_until_ms is not None:
        if utime.ticks_diff(utime.ticks_ms(), _pub_pause_until_ms) < 0:
            return False

    if isinstance(value, float):
        payload = "{:.3f}".format(value)
    else:
        payload = str(value)

    try:
        print("pub try", feed, "=", payload)
        client.publish(base + feed, payload)
        print("pub ok", feed)
        return True
    except Exception as exc:
        print("pub err", feed, exc)
        if not _try_reconnect():
            _pub_pause_until_ms = utime.ticks_add(
                utime.ticks_ms(), RECONNECT_BACKOFF_S * 1000
            )
            return False
        try:
            print("pub retry try", feed, "=", payload)
            client.publish(base + feed, payload)
            print("pub retry ok", feed)
            _pub_pause_until_ms = None
            return True
        except Exception as exc2:
            print("publish after reconnect failed:", exc2)
            _pub_pause_until_ms = utime.ticks_add(
                utime.ticks_ms(), RECONNECT_BACKOFF_S * 1000
            )
            return False


def check_controls():
    if client is None:
        return
    try:
        client.check_msg()
    except Exception as exc:
        print("mqtt check err:", exc)
        _try_reconnect()


def publish_status(force=False, output=None):
    """Publish only non-control status feeds.

    Important: setpoint-temp, system-enable, test-number, test-duration-s,
    and system-reset are control feeds from the dashboard to the ESP32.
    Publishing back to those same feeds can block or fight the dashboard state,
    so this function does not publish to them.
    """
    global _last_status_publish_ms, _last_cooling_state
    if utime is None:
        return

    now = utime.ticks_ms()
    if not force and _last_status_publish_ms is not None:
        if utime.ticks_diff(now, _last_status_publish_ms) < STATUS_PERIOD_S * 1000:
            return

    # Safe dashboard status feed. This one exists in your Adafruit IO list.
    publish(feed_name("FEED_ELAPSED_TEST_S", "elapsed-test-s"), elapsed_test_s())

    # Optional extra status feeds. Leave disabled unless these feeds exist.
    if PUBLISH_EXTRA_STATUS_FEEDS:
        cooling_on = bool(state["system_enabled"] and output is not None and output > 0.001)
        publish(feed_name("FEED_RELAY_STATE", "relay-state"), 1 if cooling_on else 0)
        cooling_state = "ON" if cooling_on else "OFF"
        if force or cooling_state != _last_cooling_state:
            publish(feed_name("FEED_COOLING_STATE", "cooling-state"), cooling_state)
            _last_cooling_state = cooling_state

    _last_status_publish_ms = now


def publish_telemetry(temp, pwm_pct, force=False):
    global _last_telemetry_publish_ms
    if temp is None or pwm_pct is None:
        return

    now = utime.ticks_ms()
    if not force and _last_telemetry_publish_ms is not None:
        if utime.ticks_diff(now, _last_telemetry_publish_ms) < TELEMETRY_PERIOD_S * 1000:
            return

    publish(feed_name("FEED_TEMPERATURE_1", "temperature1"), float(temp))
    publish("pwm-duty", float(pwm_pct))
    _last_telemetry_publish_ms = now


def set_local_enabled(enabled, reason=None):
    state["system_enabled"] = bool(enabled)
    if enabled:
        state["test_start_s"] = time.time()
        state["run_needs_prime"] = True
        screen("SYSTEM ENABLED", reason or "remote start")
    else:
        force_outputs_off()
        screen("SYSTEM DISABLED", reason or "actuators OFF")
    publish_status(force=True, output=0.0)


def handle_fault(reason):
    global _last_fault
    _last_fault = str(reason)
    print("fault:", _last_fault)
    force_outputs_off()
    state["system_enabled"] = False
    screen("FAULT", _last_fault[:16], "system disabled")
    publish_status(force=True, output=0.0)


def on_message(topic, msg):
    feed = as_text(topic).split("/")[-1]
    msg_s = as_text(msg)
    print("rx", feed, "=", msg_s)

    try:
        if feed == FEED_SETPOINT_TEMP:
            state["setpoint_temp"] = clamp(float(msg_s), 10.0, 30.0)

        elif feed == FEED_SYSTEM_ENABLE:
            requested = as_bool(msg_s)
            if requested and not state["system_enabled"]:
                set_local_enabled(True, "remote start")
            elif not requested and state["system_enabled"]:
                set_local_enabled(False, "remote stop")
            else:
                state["system_enabled"] = requested
                if not requested:
                    force_outputs_off()
                publish_status(force=True, output=0.0)

        elif feed == FEED_TEST_NUMBER:
            state["test_number"] = max(1, int(float(msg_s)))
            state["test_start_s"] = time.time()
            publish(feed_name("FEED_ELAPSED_TEST_S", "elapsed-test-s"), 0)

        elif feed == FEED_TEST_DURATION_S:
            state["test_duration_s"] = max(0, int(float(msg_s)))

        elif feed == FEED_SYSTEM_RESET:
            if as_bool(msg_s):
                screen("REMOTE RESET", "restarting")
                force_outputs_off()
                time.sleep(1)
                reset()


    except Exception as exc:
        print("bad control value for", feed, ":", msg_s, exc)


def ch0_to_od(ch0):
    blank = getattr(cfg, "OD_BLANK_CH0", None)
    if blank is None:
        blank = getattr(cfg, "OD_BLANK_LUX", None)
    if blank is None or blank <= 0 or ch0 is None or ch0 <= 0:
        return None
    return max(0.0, math.log10(float(blank) / float(ch0)))


def wait_with_controls(seconds):
    deadline = utime.ticks_add(utime.ticks_ms(), int(seconds * 1000))
    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        check_controls()
        if not state["system_enabled"]:
            force_outputs_off()
            return False
        if button_pressed():
            set_local_enabled(False, "button stop")
            return False
        utime.sleep_ms(100)
    return True


def pump_and_measure(pump_seconds, light_log):
    if not state["system_enabled"]:
        force_outputs_off()
        return False

    print("PUMP DEBUG: ON at", time.time())
    pump.value(1)
    screen("PUMP ON", "{} s".format(pump_seconds))
    if not wait_with_controls(pump_seconds):
        pump.value(0)
        print("PUMP DEBUG: OFF early at", time.time())
        return False
    pump.value(0)
    print("PUMP DEBUG: OFF at", time.time())
    
    screen("MEASURING CH0", "{} s".format(CH0_BURST_S))
    light.active(True)
    deadline = utime.ticks_add(utime.ticks_ms(), CH0_BURST_S * 1000)
    total = 0
    n = 0

    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        check_controls()
        if not state["system_enabled"]:
            force_outputs_off()
            light.active(False)
            return False
        try:
            ch0, _ch1 = light.read(raw=True)
            total += ch0
            n += 1
        except Exception as exc:
            print("ch0 read err:", exc)

    light.active(False)

    if n == 0:
        screen("LIGHT ERR", "no valid CH0")
        if light_log is not None:
            light_log.write("{},,0,\n".format(time.time()))
            light_log.flush()
        return False

    avg = total / n
    od = ch0_to_od(avg)

    publish(feed_name("FEED_LIGHT", "light"), float(avg))
    if od is not None:
        publish(feed_name("FEED_OD_WATER", "od-water"), float(od))

    if light_log is not None:
        light_log.write(
            "{},{:.2f},{},{}\n".format(
                time.time(),
                avg,
                n,
                "" if od is None else "{:.4f}".format(od),
            )
        )
        light_log.flush()

    print("CH0 avg {:.2f} n={} OD={}".format(avg, n, od))
    return True


def pi_step(temperature):
    global _integral
    dt = CONTROL_PERIOD_MS / 1000.0
    error = temperature - state["setpoint_temp"]
    unclamped = cfg.Kp * error + cfg.Ki * (_integral + error * dt)
    output = max(0.0, min(1.0, unclamped))

    if output == unclamped or (output >= 1.0 and error < 0) or (output <= 0.0 and error > 0):
        _integral += error * dt
    return output, error


def set_pwm(output):
    if not state["system_enabled"]:
        output = 0.0
    pwm.duty(int(output * 1023))


def maybe_advance_test_window():
    duration = int(state["test_duration_s"])
    if duration <= 0:
        return
    if elapsed_test_s() >= duration:
        state["test_number"] += 1
        state["test_start_s"] = time.time()
        print("test number auto-advanced locally:", state["test_number"])
        publish(feed_name("FEED_ELAPSED_TEST_S", "elapsed-test-s"), 0)


def init_hardware():
    global pwm, pump, therm
    gc.collect()
    try:
        print("mem free before hardware init:", gc.mem_free())
    except Exception:
        pass
    pwm = PWM(Pin(cfg.MOSFET_PWM), freq=cfg.MOSFET_PWM_FREQ)
    pwm.duty(0)
    pump = Pin(PUMP_PIN, Pin.OUT)
    pump.value(0)
    gc.collect()
    try:
        print("mem free before thermistor ADC:", gc.mem_free())
    except Exception:
        pass
    therm = Thermistor(
        pin_no=cfg.THERMISTOR_1_PIN,
        adc_lookup=cfg.PIN36_ADC_LOOKUP,
    )
    print("hardware init ok")


def self_test():
    global light
    screen("SELF TEST", "...")

    temp = therm.read()
    if temp is None or not (MIN_VALID_TEMP_C <= temp <= MAX_VALID_TEMP_C):
        raise RuntimeError("thermistor self-test failed: {}".format(temp))

    i2c = get_i2c()
    light = LTR329(i2c, measurement_rate=100)
    ch0, _ch1 = light.read(raw=True)

    screen("Thermistor OK", "{:.1f} C".format(temp), "Light OK", "CH0={}".format(ch0))
    print("selftest ok T={:.2f}C CH0={}".format(temp, ch0))
    return temp, ch0


def close_logs(*files):
    for handle in files:
        try:
            if handle is not None:
                handle.flush()
                handle.close()
        except Exception:
            pass


def experiment_loop(temp_log, light_log):
    global _integral
    _integral = 0.0
    consec_errors = 0
    flush_count = 0
    last_pump_ms = utime.ticks_ms()

    while state["system_enabled"]:
        loop_start = utime.ticks_ms()
        check_controls()

        if button_pressed():
            set_local_enabled(False, "button stop")
            break

        if not state["system_enabled"]:
            break

        maybe_advance_test_window()

        try:
            temp = therm.read()
            if temp is None:
                raise ValueError("sensor None")
            if not (MIN_VALID_TEMP_C <= temp <= MAX_VALID_TEMP_C):
                raise ValueError("temp {} out of range".format(temp))

            output, error = pi_step(temp)
            set_pwm(output)
            consec_errors = 0
        except Exception as exc:
            consec_errors += 1
            force_outputs_off()
            screen("FAULT #{}".format(consec_errors), str(exc)[:16], "duty -> 0")
            print("control fault:", exc)
            publish_status(force=True, output=0.0)
            if consec_errors >= MAX_CONSEC_ERRORS:
                handle_fault("{} faults".format(consec_errors))
                break
            utime.sleep_ms(CONTROL_PERIOD_MS)
            continue

        pwm_pct = output * 100.0
        if temp_log is not None:
            temp_log.write(
                "{},{:.3f},{:.1f},{:.3f},{:.1f},{},{}\n".format(
                    time.time(),
                    temp,
                    pwm_pct,
                    error,
                    state["setpoint_temp"],
                    state["test_number"],
                    elapsed_test_s(),
                )
            )
            flush_count += 1
            if flush_count >= LOG_FLUSH_EVERY:
                temp_log.flush()
                flush_count = 0

        screen(
            "RUNNING",
            "SP {:.1f}C".format(state["setpoint_temp"]),
            "T {:.2f}C".format(temp),
            "Err {:.2f}".format(error),
            "PWM {:.1f}%".format(pwm_pct),
            "t {}s".format(elapsed_test_s()),
        )

        publish_telemetry(temp, pwm_pct)
        publish_status(output=output)

        if utime.ticks_diff(utime.ticks_ms(), last_pump_ms) >= PUMP_INTERVAL_S * 1000:
            pump_and_measure(EXP_PUMP_S, light_log)
            last_pump_ms = utime.ticks_ms()

        elapsed = utime.ticks_diff(utime.ticks_ms(), loop_start)
        remaining = CONTROL_PERIOD_MS - elapsed
        while remaining > 0 and state["system_enabled"]:
            check_controls()
            if button_pressed():
                set_local_enabled(False, "button stop")
                break
            nap = 100 if remaining > 100 else remaining
            utime.sleep_ms(nap)
            remaining -= nap

    force_outputs_off()
    publish_status(force=True, output=0.0)


def idle_loop():
    screen("WiFi + MQTT up", "system disabled", "waiting for enable")
    print("idle: waiting for Adafruit IO system-enable=1 or button press")
    # Do not publish to control feeds while idle; just listen for MQTT commands.

    last_idle_print = time.time()

    while not state["system_enabled"]:
        check_controls()
        if button_pressed():
            set_local_enabled(True, "button start")
            break
        # Do not publish while idle; keep MQTT free to receive dashboard commands.
        if time.time() - last_idle_print >= 5:
            print("idle heartbeat: MQTT listening, system-enable={} setpoint={} test={} elapsed={}s".format(
                state["system_enabled"],
                state["setpoint_temp"],
                state["test_number"],
                elapsed_test_s(),
            ))
            last_idle_print = time.time()
        if _last_fault:
            screen("IDLE", _last_fault[:16], "waiting enable")
        time.sleep(0.2)


def run_session():
    temp_log = None
    light_log = None

    try:
        self_test()
    except Exception as exc:
        handle_fault(exc)
        return

    try:
        temp_log = open(TEMP_LOG_FILE, "w")
        temp_log.write(
            "time_s,temp_C,pwm_pct,error,setpoint_C,test_number,elapsed_test_s\n"
        )
        light_log = open(LIGHT_LOG_FILE, "w")
        light_log.write("time_s,ch0_avg,n_samples,od_estimate\n")

        if state["run_needs_prime"]:
            if pump_and_measure(PRIME_PUMP_S, light_log):
                state["run_needs_prime"] = False

        if state["system_enabled"]:
            experiment_loop(temp_log, light_log)

    except Exception as exc:
        handle_fault(exc)
    finally:
        close_logs(temp_log, light_log)


def main():
    wifi_connect()
    load_mqtt_module()

    # Load sensor modules and allocate ADC/PWM before opening the MQTT socket.
    # On ESP32/MicroPython, ADC oneshot allocation can fail with ENOMEM if it is
    # done after Wi-Fi + MQTT + the large thermistor lookup tables are already live.
    load_runtime_modules()
    print("initialising hardware before MQTT socket...")
    init_hardware()

    mqtt_connect()
    print("skipping initial status publish; dashboard control feeds are subscribe-only")
    print("entering main loop")

    while True:
        if not state["system_enabled"]:
            idle_loop()
        if state["system_enabled"]:
            run_session()


main()