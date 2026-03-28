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
import select
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import json

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

def get_chip_temp():
    return microcontroller.cpu.temperature

# ---------------------------------------------------
# Adafruit API Functions
def get_feed(feed_name):
    try:
        # get feed
        picow_feed = io.get_feed(feed_name)
        print(f"Got feed: {feed_name}")  

    except AdafruitIO_RequestError:
        # if no feed exists, create one
        print(f"Feed not found: {feed_name}")
        picow_feed = io.create_new_feed(feed_name)
    
    return picow_feed["key"]

def send_to_adafruit(feed_key, value):
    # sends the server node's temperature data as default, if not otherwise specified
    try:
        io.send_data(feed_key, value)
        print(f"Sent to Adafruit {feed_key}: {value}")

    except Exception as e:
        print(f"Error sending {value} to Adafruit IO {feed_key}: {e}")
# ---------------------------------------------------
# IoT Functions
def add_data_pack(ip, data):
    # data_pack = (data, time.time())
    data_pack = data
    # clients_data[ip].append(data_pack)
    clients_data[ip] = data_pack
    print(f"{data_pack} added to {ip} client data")

def send_self_data(last_send_time):
    current_time = time.time()

    if current_time - last_send_time >= 1:
        # 1 second has passed --> send data
        # send_to_adafruit(feeds["14"], "{:.2f}".format(get_temp_avg(5)))
        temp_value = "{:.2f}".format(get_temp_avg(5))
        CPU_temp = "{:.2f}".format(get_chip_temp())
        add_data_pack(UDP_IP.split('.')[-1], (temp_value, CPU_temp))
        last_send_time = current_time
    
    return last_send_time

def receive_data(buffer):
    try:
        size, client_address = udp_server.recvfrom_into(buffer)
        data = buffer[:size]
        data = data.decode().split(",")
        temp_value = "{:.2f}".format(float(data[0]))
        CPU_temp = "{:.2f}".format(float(data[1]))
        print(f"Received message: {temp_value}, {CPU_temp} from {client_address[0].split('.')[-1]}")
        # send_to_adafruit(feeds[str(client_address[0][-2:])], data.decode())
        add_data_pack(client_address[0].split('.')[-1], (temp_value, CPU_temp))
    except OSError as e:
        if e.errno == 11:
            pass
        else:
            print(f"Receive Data Error: {e}")
# --------------------------------------------------    -
# Webpage Functions
def generate_page():
    html = """
    <html>
    <head>
    <title>Sensor Node Data</title>
    <meta http-equiv="refresh" content="2">
    <style>
    body { font-family: Arial; background:#111; color:white; }
    table { border-collapse: collapse; width:50%; }
    th, td { border:1px solid white; padding:8px; text-align:center; }
    th { background:#333; }
    </style>
    </head>
    <body>
    <h1>Sensor Node Dashboard</h1>
    <table>
    <tr><th>Client IP</th><th>Latest Data</th><th>CPU Temp</th></tr>
    
    <script>
    async function fetchData() {
        try {
            const res = await fetch('/data');
            const json = await res.json();
            const tbody = document.getElementById('data-body');
            tbody.innerHTML = '';
            for (const [ip, value] of Object.entries(json)) {
                tbody.innerHTML += `<tr><td>${ip}</td><td>${value[0]}</td><td>${value[1]}</td></tr>`;
            }
        } catch (e) {
            console.log('Fetch error:', e);
        }
    }

    setInterval(fetchData, 1000); # fetches data every second
    fetchData();
    </script>
    """

    for ip, data in clients_data.items():
        html += f"<tr><td>{ip}</td><td>{data[0]}</td><td>{data[1]}</tr>"

    html += """
    </table>
    </body>
    </html>
    """
    # print(html)
    # print(str(html))
    return str(html)

def serve(buffer):
    try:
        # Check if a connection is actually ready before accepting
        readable, _, _ = select.select([web_socket], [], [], 0)
        if not readable:
            return  # nothing waiting, skip immediately
        
        connection, addr = web_socket.accept()
        print("Connection accepted")
        
        # Wait for request data to arrive
        readable, _, _ = select.select([connection], [], [], 2)
        if not readable:
            connection.close()
            return
            
        request = connection.recv_into(buffer)
        print(f"Received request: {request}")

        # size = connection.recv_into(memoryview(buffer))
        # request = buffer[:size].decode()

        # Route based on request
        if 'GET /data' in request:
            # Build JSON manually (no json library needed)
            json_parts = []
            for ip, data in clients_data.items():
                json_parts.append(f'"{ip}":"{data}"')
            json_body = '{' + ','.join(json_parts) + '}'
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{json_body}"
        else:
            # Serve the main page
            html = generate_page()
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{html}"

        # html = generate_page()
        # response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{html}"
        connection.send(response.encode())
        connection.close()
        print("Webpage served")

    except OSError as e:
        if e.errno == 11:
            pass
        else:
            print(f"Webpage Error: {e}")
    # finally:
        #connection.close()
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

UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
udp_server.setblocking(False)
print(f"Server listening on {UDP_IP}:{UDP_PORT}")
# ---------------------------------------------------
# Adafruit Setup
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

# Initialize an Adafruit IO HTTP API object
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)
print("connected to io")

# Get feeds for each underground node
feeds = {
    "14": get_feed("picow14"),
    "141": get_feed("picow141"),
    "142": get_feed("picow142"),
    "42": get_feed("picow42")
}
# ---------------------------------------------------
# Webpage Setup
web_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
web_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
web_socket.bind((UDP_IP, 8080))
web_socket.listen(1)
web_socket.setblocking(False)
print(f"Web dashboard at http://{UDP_IP}:8080")
# ---------------------------------------------------

buffer = bytearray(1024)
last_send_time = 0
clients_data = {}
# Initialize empty data lists for each client feed
for feed in feeds:
    clients_data[feed] = (None, None)

try:
    print("Waiting for data...")
    while True:
        
       # try:
        last_send_time = send_self_data(last_send_time)

        receive_data(buffer)

        serve(buffer)
        time.sleep(0.05)
        #except Exception as e:
           # print(f"Error: {e}")
finally:
    udp_server.close()
    web_socket.close()
    print("Connection closed")
