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
import ipaddress
import ssl
import adafruit_ntp
import rtc
import adafruit_minimqtt.adafruit_minimqtt as MQTT


# ---------------------------------------------------
# Thermistor Functions
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
def mqtt_publish(node, temp_value):
    try:
        unix_time = time.time() + EPOCH_OFFSET
        payload = json.dumps({"temp": float("{:.2f}".format(float(temp_value))), "timestamp": unix_time}) # convert to JSON string
        mqtt_client.publish(f"nodes/{node}/data", payload)
        print(f"Published to MQTT: {node} = {temp_value}°C, {unix_time}")
    except Exception as e:
        print(f"MQTT Error: {e}")

def send_self_data(last_send_time):
    current_time = time.time()

    if current_time - last_send_time >= 1:
        # 1 second has passed --> send data
        # temp_value = "{:.2f}".format(get_temp_avg(5))
        mqtt_publish("picow14", get_temp_avg(5))
        last_send_time = current_time
    
    return last_send_time

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
# wifi.radio.set_ipv4_address(ipv4=ipaddress.IPv4Address("10.164.2.14"), netmask=ipaddress.IPv4Address("255.255.255.0"), gateway=ipaddress.IPv4Address("10.80.223.222"))
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
# wifi.radio.ipv4_dns = ipaddress.IPv4Address("8.8.8.8") # use Google's DNS
print("Connected to Wi-Fi")
# ---------------------------------------------------
# Server Setup
try:
    pool = socketpool.SocketPool(wifi.radio)
    udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
except Exception as e:
    print(f"Socket Error: {e}")

# sync Pico's Real Time Clock to Network Time Protocol on the internet
try:
    ntp = adafruit_ntp.NTP(pool, tz_offset=0)
    rtc.RTC().datetime = ntp.datetime
    EPOCH_OFFSET = 0
except Exception as e:
    print(f"Clock Error: {e}")
    EPOCH_OFFSET = 946684800 # seconds from 2000-01-01 (Pico) to 1970-01-01 (Unix)

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

try:
    mqtt_client.connect()
except Exception as e:
    print(f"MQTT Connection Error: {e}")
# ---------------------------------------------------
    
buffer = bytearray(1024)
last_send_time = 0

try:
    print("Waiting for data...")
    while True:
        
       # try:
        last_send_time = send_self_data(last_send_time)

        # receive_data(buffer)

        mqtt_client.loop()

        time.sleep(0.05)
        #except Exception as e:
           # print(f"Error: {e}")
finally:
    udp_server.close()
    mqtt_client.disconnect()
    print("Connection closed")