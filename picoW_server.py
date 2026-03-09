import os
import ipaddress
import wifi
import socketpool
import adafruit_requests
import time

# aio configuration
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

# Static IP address configuration
STATIC_IP = "10.164.2.14"
print()
print("Connecting to WiFi...")

#  connect to your SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to WiFi")

print("IP:", wifi.radio.ipv4_address) #  prints IP address to REPL

pool = socketpool.SocketPool(wifi.radio)
server_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
server_socket.bind((str(wifi.radio.ipv4_address), 5000))
server_socket.listen(1)

print("Server is listening on port 5000...")



while True:
    connection, address = server_socket.accept()
    print("Connection from:", address)

    data = connection.recv(1024)
    print("Received data:", data)
    if data:
        print("Received data:", data)
