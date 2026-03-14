# picoW_server.py

import os
import time
import board
import analogio
import math
import wifi
import socketpool
import ipaddress
import ssl
import microcontroller
import busio
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

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


# Thermistor setup
adc = analogio.AnalogIn(board.GP26)
series_resistor = 10000
nominal_resistance = 10000
nominal_temp = 25
beta = 3950

aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to Wi-Fi")
print("Server IP Address:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
print(f"Server listening on {UDP_IP}:{UDP_PORT}")

# Initialize an Adafruit IO HTTP API object
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)
print("connected to io")

try:
# get feed
    picowTemp_feed = io.get_feed("praxisiii")
    print("got feed: praxisiii")
    
except AdafruitIO_RequestError:
# if no feed exists, create one
    print("Feed not found")
    picowTemp_feed = io.create_new_feed("PraxisIII")
    
feed_name = picowTemp_feed["key"]
print("feeds created")

buffer = bytearray(1024)

try:
    while True:
        print("Waiting for data...")
        try:
            while True:
                temp_c = get_temp_avg(5)
                msg = "{:.2f}".format(temp_c)
                io.send_data(feed_name, msg)
                print("Sent:", msg)
                time.sleep(1)
                
            size, client_address = udp_server.recvfrom_into(buffer)
            data = buffer[:size]
            io.send_data(feed_name, data.decode())
            print(f"sent {data.decode()} to adafruit")
            print(f"Received message: {data.decode()} from {client_address}")
            response = "Message received!"
            # udp_server.sendto(response.encode(), client_address)
            # print(f"Sent response to {client_address}")
            
            
                
        except Exception as e:
            print(f"Error: {e}")
finally:
    udp_server.close()
    print("Connection closed")
