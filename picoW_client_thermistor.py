import time
import board
import analogio
import math
import wifi
import socketpool
import os
import ipaddress


# -------------------------------
# Thermistor setup
# -------------------------------
adc = analogio.AnalogIn(board.GP26)
series_resistor = 10000
nominal_resistance = 10000
nominal_temp = 25
beta = 3950

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

# -------------------------------
# Connect to Wi-Fi using settings.toml
# -------------------------------
print("Connecting to Wi-Fi...")
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected! IP address:", wifi.radio.ipv4_address)


# -------------------------------
# UDP setup
# -------------------------------
pool = socketpool.SocketPool(wifi.radio)
udp = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
UDP_IP = "10.164.2.14"  # ip address of hotspot 
UDP_PORT = 5000 #both sender and receiver have to go to the same port

while True:
    temp_c = get_temp_avg(5)
    msg = "{:.2f}".format(temp_c)
    udp.sendto(msg.encode(), (UDP_IP, UDP_PORT))
    print("Sent:", msg)
    time.sleep(1)
