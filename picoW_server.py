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
import select

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
# Send Data Functions

# Send Data via Wifi to Anemometer
def send_to_anemometer(last_send_time):
    current_time = time.monotonic()

    if current_time - last_send_time >= 0.8:
        # 1 second has passed --> send data
        # temp_value = "{:.2f}".format(get_temp_avg(5))
        temp_value = get_temp_avg(5)
        data = {"node": "picow14", "temp": temp_value}
        msg = json.dumps(data) # convert data dict to JSON string
        transmission_udp.sendto(msg.encode(), (ANEMOMETER_IP, ANEMOMETER_PORT))
        print("Sent:", msg)
        last_send_time = current_time
    return last_send_time

# Receive UDP Data
def receive_data(buffer):
    try:
        # Check if a connection is actually ready before accepting
        readable, _, _ = select.select([udp_server], [], [], 0.5) # 500 ms timeout
        if not readable:
            return  # nothing waiting, skip immediately
        
        size, client_address = udp_server.recvfrom_into(buffer)
        data = buffer[:size]
        print(f"Received message: {data.decode()} from {client_address}")
        temp_value = float(data.decode())
        data = {"node": f"picow{client_address[0].split('.')[-1]}", "temp": temp_value}
        msg = json.dumps(data) # convert data dict to JSON string
        transmission_udp.sendto(msg.encode(), (ANEMOMETER_IP, ANEMOMETER_PORT))
        print(f"Sent message: {msg} from {client_address}")
        # mqtt_publish(node, data.decode())      
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
# ---------------------------------------------------
# UDP Server Setup
try:
    pool = socketpool.SocketPool(wifi.radio)
    print("Pool Connected")
    udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    print("Server Created")
except Exception as e:
    print(f"Socket Error: {e}")

UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
udp_server.setblocking(False)
print(f"Server listening on {UDP_IP}:{UDP_PORT}")
# ---------------------------------------------------
# UDP Transmission Setup
transmission_pool = socketpool.SocketPool(wifi.radio)
transmission_udp = transmission_pool.socket(transmission_pool.AF_INET, transmission_pool.SOCK_DGRAM)
ANEMOMETER_IP = os.getenv('ANEMOMETER_IP') # ip address of hotspot 
ANEMOMETER_PORT = 5000 #both sender and receiver have to go to the same port
# ---------------------------------------------------
# Main

buffer = bytearray(1024)
last_send_time = 0

print("Waiting for data...")
try:
    while True:
        last_send_time = send_to_anemometer(last_send_time)

        receive_data(buffer)

        time.sleep(0.05)

except Exception as e:
    print(f"Main Loop Error: {e}")