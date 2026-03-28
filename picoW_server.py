# picoW_server.py
# picoW --> MQTT broker --> Web Dashboard
#               |
#           Flask API (Render) --> Database (Supabase)

import json
import os
import time
import board
import analogio
import math
import wifi
import socketpool
import ssl
import adafruit_ntp
import rtc
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import supervisor
import adafruit_requests
import select
import numpy as np

# Thermistor Functions
series_resistor = 10000
nominal_resistance = 10000
nominal_temp = 25
beta = 3950

adc = analogio.AnalogIn(board.GP26)

def get_temp(adc_value):
    voltage = adc_value / 65535 * 3.3
    resistance = series_resistor * (voltage / (3.3 - voltage))
    temp_k = 1 / (1/(nominal_temp+273.15) + (1/beta)*math.log(resistance/nominal_resistance))
    return temp_k - 273.15

def get_temp_avg(samples=5):
    total = 0
    for _ in range(samples):
        total += get_temp(adc.value)
    return total / samples
# ---------------------------------------------------
# IoT Functions (MQTT)
def connect_mqtt(retries=5, delay=5):
    global pool, mqtt_client
    for attempt in range(retries):
        try:
            print(f"MQTT connecting (attempt {attempt+1}/{retries})...")
            mqtt_client.connect()
            print("MQTT connected")
            return True
        except Exception as e:
            print(f"MQTT Connection Error: {e}")
            if attempt >= retries/2:

                pool = socketpool.SocketPool(wifi.radio)
                mqtt_client = MQTT.MQTT(
                    broker="339f0d63410548358f66c3cb882ec424.s1.eu.hivemq.cloud",
                    port=8883,
                    username=os.getenv('MQTT_USERNAME'),
                    password=os.getenv('MQTT_PASSWORD'),
                    socket_pool=pool,
                    is_ssl=True,
                    ssl_context=ssl.create_default_context()
                )
                
            if attempt < retries - 1:
                print(f"Waiting {delay}s before retry...")
                time.sleep(delay)
    return False

def mqtt_publish(node, temp_value):
    try:
        unix_time = time.time() + EPOCH_OFFSET
        payload = json.dumps({"temp": float("{:.2f}".format(float(temp_value))), "timestamp": unix_time}) # convert to JSON string
        mqtt_client.publish(f"nodes/{node}/data", payload)
        print(f"Published to MQTT: {node} = {temp_value}°C, {unix_time}")
    except Exception as e:
        print(f"MQTT Publish Error: {e}")

def send_self_data(last_send_time):
    current_time = time.monotonic()

    if current_time - last_send_time >= 0.8:
        # 1 second has passed --> send data
        # temp_value = "{:.2f}".format(get_temp_avg(5))
        mqtt_publish("picow14", get_temp_avg(5))
        last_send_time = current_time
    return last_send_time

# Receive UDP Data
def receive_data(buffer):
    try:
        size, client_address = udp_server.recvfrom_into(buffer)
        data = buffer[:size]
        print(f"Received message: {data.decode()} from {client_address}")
        node = f"picow{client_address[0].split('.')[-1]}"
        mqtt_publish(node, data.decode())      
    except OSError as e:
        if e.errno == 11:
            pass
        else:
            print(f"Receive Data Error: {e}")
# ---------------------------------------------------
# Thermistor Setup
adc = analogio.AnalogIn(board.GP26)
series_resistor = 10000
nominal_resistance = 10000
nominal_temp = 25
beta = 3950
# ---------------------------------------------------
# Wifi Setup
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to Wi-Fi")
print(f"IP Address: {wifi.radio.ipv4_address}")
print(f"Subnet Mask: {wifi.radio.ipv4_subnet}")
print(f"Gateway: {wifi.radio.ipv4_gateway}")
print(f"DNS: {wifi.radio.ipv4_dns}")

# wifi.radio.set_ipv4_address(
#     ipv4=ipaddress.IPv4Address("10.80.223.14"),
#     netmask=ipaddress.IPv4Address("255.255.255.0"),
#     gateway=ipaddress.IPv4Address("10.80.223.222"))

#     #ipv4_dns=ipaddress.IPv4Address("8.8.8.8")) # use Google's DNS

# print("IP Address changed:")
# print(f"IP Address: {wifi.radio.ipv4_address}")
# print(f"Subnet Mask: {wifi.radio.ipv4_subnet}")
# print(f"Gateway: {wifi.radio.ipv4_gateway}")
# print(f"DNS: {wifi.radio.ipv4_dns}")

# ---------------------------------------------------
# Server Setup
try:
    pool = socketpool.SocketPool(wifi.radio)
    print("Pool Connected")
    udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    print("Server Created")
except Exception as e:
    print(f"Socket Error: {e}")

# sync Pico's Real Time Clock to Network Time Protocol on the internet
try:
    ntp = adafruit_ntp.NTP(pool, tz_offset=0)
    rtc.RTC().datetime = ntp.datetime
    EPOCH_OFFSET = 0
    print("NTP Synced")
except Exception as e:
    print(f"Clock Error: {e}")
    current_time = time.time()
    if current_time < 946684800: # NTP not synced --> Pico Epoch
        EPOCH_OFFSET = 946684800 # seconds from 2000-01-01 (Pico) to 1970-01-01 (Unix)
        print("Epoch Offset Used")
    else:
        EPOCH_OFFSET = 0

UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
udp_server.setblocking(False)
print(f"Server listening on {UDP_IP}:{UDP_PORT}")
# ---------------------------------------------------
# MQTT Broker Setup
mqtt_client = MQTT.MQTT(
    broker="339f0d63410548358f66c3cb882ec424.s1.eu.hivemq.cloud",
    port=8883, # TSL port
    username=os.getenv('MQTT_USERNAME'),
    password=os.getenv('MQTT_PASSWORD'),
    socket_pool=pool,
    is_ssl=True,
    ssl_context=ssl.create_default_context()
)

mqtt_connected = connect_mqtt(retries=5, delay=5)
if not mqtt_connected:
    print("MQTT failed after all retries. Restarting...")
    time.sleep(2)
    supervisor.reload()

# ---------------------------------------------------
    
buffer = bytearray(1024)
last_send_time = 0

print("Waiting for data...")
try:
    while True:
        last_send_time = send_self_data(last_send_time)

        receive_data(buffer)
        
        try:
            mqtt_client.loop()
        except Exception as e:
            print(f"MQTT Loop Error: {e}")
            print("MQTT Reconnecting...")
            time.sleep(5)
            mqtt_connected = connect_mqtt(retries=5, delay=5)
            if not mqtt_connected:
                supervisor.reload()

        time.sleep(0.05)
finally:
    udp_server.close()
    try:
        mqtt_client.disconnect()
    except Exception as e:
        print(f"MQTT  Disconnect Error: {e}")
    print("Connection closed")
