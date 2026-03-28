# picoW_anemometer.py
# picoW Gateway Node --> Anemometer --> MQTT broker --> Web Dashboard
#red 11 (gp16), orange 13 (gnd) yellow 26 3v3

# ---------------------------------------------------
from machine import Pin
import time
import network
import socket
import json
from umqtt.simple import MQTTClient
import config
import select
import ntptime

# ---------------------------------------------------
# Configuration
MICROPY_WIFI_SSID = config.MICROPY_WIFI_SSID
MICROPY_WIFI_PASSWORD = config.MICROPY_WIFI_PASSWORD
MQTT_BROKER = config.MQTT_BROKER
MQTT_PORT = config.MQTT_PORT
MQTT_USERNAME = config.MQTT_USERNAME
MQTT_PASSWORD = config.MQTT_PASSWORD
# ---------------------------------------------------
# Anemometer Constants
HALL_PIN = 16
PULSES_PER_REV = 2
radius = 0.3
CALIBRATION_FACTOR = 1.0
SAMPLE_TIME = 1.0
DEBOUNCE_MS = 3
UDP_PORT = 5000
# ---------------------------------------------------
# Global Variables
pulse_count = 0
last_trigger_ms = 0
# ---------------------------------------------------
# INTERRUPT CALLBACK
def hall_callback(pin):
    global pulse_count, last_trigger_ms

    now = time.ticks_ms()
    if time.ticks_diff(now, last_trigger_ms) > DEBOUNCE_MS:
        pulse_count += 1
        last_trigger_ms = now
# ---------------------------------------------------
# HALL EFFECT SENSOR SETUP
hall_sensor = Pin(HALL_PIN, Pin.IN, Pin.PULL_UP)
hall_sensor.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=hall_callback)
# ---------------------------------------------------
# Wifi Setup
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(MICROPY_WIFI_SSID, MICROPY_WIFI_PASSWORD)

    print("Connecting to WiFi...")
    while not wlan.isconnected():
        time.sleep(1)

    print("Connected to IP:", wlan.ifconfig())
    return wlan

def sync_time():
    global EPOCH_OFFSET
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()  # sets the internal RTC to UTC
        print("Time synchronized via NTP")
        EPOCH_OFFSET = 0
    except Exception as e:
        EPOCH_OFFSET = 946684800
        print("NTP sync failed, using local time with offset:", EPOCH_OFFSET)
        print("NTP sync failed:", e)

def local_timestamp():
    return time.time() + EPOCH_OFFSET
# ---------------------------------------------------
# MQTT Setup
def connect_mqtt(retries=5, delay=2):
    global mqtt

    for attempt in range(retries):
        try:
            print("MQTT connecting (attempt", attempt + 1, "/", retries, ")...")
            client = MQTTClient(
                client_id="pico_w",
                server=MQTT_BROKER,
                port=MQTT_PORT,
                user=MQTT_USERNAME,
                password=MQTT_PASSWORD
            )
            client.connect()
            print("MQTT connected")
            return client

        except Exception as e:
            print("MQTT Connection Error:", e)

            # try reconnecting WiFi too (very important)
            if not wlan.isconnected():
                print("WiFi lost. Reconnecting...")
                connect_wifi()

            time.sleep(delay)

    print("MQTT failed after retries. Restarting...")
    time.sleep(2)
    import machine
    machine.reset()

def mqtt_publish(topic, payload):
    global mqtt

    try:
        mqtt.publish(topic, payload)

    except Exception as e:
        print("Publish failed:", e)

        # reconnect and retry once
        mqtt = connect_mqtt()
        try:
            mqtt.publish(topic, payload)
            print("Re-publish success")
        except Exception as e:
            print("Re-publish failed:", e)

# ---------------------------------------------------
# WIND SPEED
def calculate_wind_speed():
    global pulse_count

    pulse_count = 0
    start_time = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start_time) < int(SAMPLE_TIME * 1000):
        time.sleep_ms(10)

    elapsed_s = SAMPLE_TIME

    rev_per_sec = (pulse_count / PULSES_PER_REV) / elapsed_s
    circumference = 2 * 3.14159265359 * radius
    wind_speed_m_s = rev_per_sec * circumference * CALIBRATION_FACTOR
    wind_speed_km_h = wind_speed_m_s * 3.6

    return wind_speed_m_s, wind_speed_km_h

# ---------------------------------------------------
# UDP Server Setup
def setup_udp():
    addr = socket.getaddrinfo("0.0.0.0", UDP_PORT)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(addr)
    s.setblocking(False)
    print("Anemometer server listening on:", wlan.ifconfig()[0], ":", UDP_PORT)
    return s

# ---------------------------------------------------
# IoT Functions (MQTT)

def receive_data(sock, buffer, all_data):
    try:
        readable, _, _ = select.select([sock], [], [], 0.5)  # 500 ms timeout
        if not readable:
            return  
        
        data_bytes, addr = sock.recvfrom(buffer)
        data = json.loads(data_bytes.decode())
        node = data.get("node")
        all_data[node] = {
            "temp": float(data.get("temp")),
            "timestamp": local_timestamp()
        }
        # print("Received:", node, all_data[node])
    except Exception as e:
        print("Receive Data Error:", e)

# ---------------------------------------------------
# Main Setup
wlan = connect_wifi()
sync_time()
mqtt = connect_mqtt()
udp_server = setup_udp()

buffer = 1024
all_data = {}
last_publish = time.time()

# ---------------------------------------------------
# Main
while True:

    receive_data(udp_server, buffer, all_data)

    # publish every 5 seconds or if enough nodes
    if (len(all_data) >= 4) or (time.time() - last_publish > 5):

        wind_speed_m_s, wind_speed_km_h = calculate_wind_speed()

        all_data["anemometer"] = {
            "wind_speed": wind_speed_m_s,
            "timestamp": local_timestamp()
        }

        print("Wind Speed: {:.2f} m/s | {:.2f} km/h".format(
            wind_speed_m_s, wind_speed_km_h))

        for node, values in all_data.items():
            topic = b"nodes/%s/data" % node.encode()
            payload = json.dumps(values)

            try:
                mqtt_publish(topic, payload)
                print("Published:", node, values)
            except Exception as e:
                print("MQTT error:", e)
                mqtt = connect_mqtt()
                
        all_data.clear()
        last_publish = time.time()