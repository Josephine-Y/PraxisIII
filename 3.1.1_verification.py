import time
import board
import analogio
import math
import wifi
import socketpool
import os

# -------------------------------------------
# Thermistor setup
# -------------------------------------------
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

# -------------------------------------------
# Internal chip temperature
# -------------------------------------------
chip_adc = analogio.AnalogIn(board.TEMPERATURE)

def get_chip_temp():
    voltage = chip_adc.value * 3.3 / 65535
    return 27 - (voltage - 0.706) / 0.001721

# -------------------------------------------
# Connect to Wi-Fi
# -------------------------------------------
print("Connecting to Wi-Fi...")
wifi.radio.connect(
    os.getenv('CIRCUITPY_WIFI_SSID'),
    os.getenv('CIRCUITPY_WIFI_PASSWORD')
)
print("Connected! IP:", wifi.radio.ipv4_address)

# -------------------------------------------
# UDP setup
# -------------------------------------------
pool = socketpool.SocketPool(wifi.radio)
udp = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

UDP_IP = "10.164.2.14"
UDP_PORT = 5000

# -------------------------------------------
# Main loop
# -------------------------------------------
while True:
    therm_temp = get_temp_avg(5)
    chip_temp = get_chip_temp()

    # Create comma-separated packet
    msg = "{:.2f},{:.2f}".format(therm_temp, chip_temp)

    udp.sendto(msg.encode(), (UDP_IP, UDP_PORT))

    print("Sent:", msg)

    time.sleep(1)
