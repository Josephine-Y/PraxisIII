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
        payload = json.dumps({"temp": temp_value, "timestamp": unix_time}) # convert to JSON string
        mqtt_client.publish(f"nodes/{node}/data", payload)
        print(f"Published to MQTT: {node} = {temp_value}°C, {unix_time}")
    except Exception as e:
        print(f"MQTT Error: {e}")

def send_self_data(last_send_time):
    current_time = time.time()

    if current_time - last_send_time >= 1:
        # 1 second has passed --> send data
        temp_value = "{:.2f}".format(get_temp_avg(5))
        mqtt_publish("picow14", temp_value)
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
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to Wi-Fi")
# ---------------------------------------------------
# Server Setup
pool = socketpool.SocketPool(wifi.radio)
udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

# sync Pico's Real Time Clock to Network Time Protocol on the internet
try:
    ntp = adafruit_ntp.NTP(pool, tz_offset=0)
    rtc.RTC().datetime = ntp.datetime
    EPOCH_OFFSET = 0
except Exception as e:
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
    ssl=True,
    ssl_context=ssl.create_default_context()
)

mqtt_client.connect()
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
    print("Connection closed")