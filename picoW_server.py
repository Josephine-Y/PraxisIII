# picoW_server_ros.py

import os
import time
import board
import analogio
import math
import wifi
import socketpool
import ssl
import microcontroller
import busio
import adafruit_requests
import select
import numpy as np
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

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

# Adafruit IO Functions
def get_feed(feed_name):
    try:
        picow_feed = io.get_feed(feed_name)
        print(f"Got feed: {feed_name}")  
    except AdafruitIO_RequestError:
        print(f"Feed not found: {feed_name}")
        picow_feed = io.create_new_feed(feed_name)
    return picow_feed["key"]

def send_to_adafruit(feed_key, value):
    try:
        io.send_data(feed_key, value)
        print(f"Sent to Adafruit {feed_key}: {value}")
    except Exception as e:
        print(f"Error sending {value} to Adafruit IO {feed_key}: {e}")

# Node locations: We'll need to place the nodes at specific locations and input their respective coordinates here before running the code
def get_node_location(ip):
    if ip == "10.164.2.14":
        return (0.0, 0.0)
    elif ip == "10.164.2.141":
        return (1.0, 0.0)
    elif ip == "10.164.2.142":
        return (0.0, 1.0)
    elif ip == "10.164.2.42":
        return (1.0, 1.0)
    else:
        return (0.0, 0.0)

# ROS Variables
TEMP_THRESHOLD = 25.0 # potentially change
last_hot_time = {}
rate_of_spread = 0.0
hot_nodes_count = 0

# IoT Functions
clients_data = {}

def add_data_pack(ip, data):
    clients_data[ip] = data
    if ip not in last_hot_time:
        last_hot_time[ip] = 0
    print(f"{data} added to {ip} client data")

def send_self_data(last_send_time):
    current_time = time.time()
    if current_time - last_send_time >= 1:
        add_data_pack(UDP_IP, "{:.2f}".format(get_temp_avg(5)))
        last_send_time = current_time
    return last_send_time

# Receive UDP Data
def receive_data(buffer):
    try:
        size, client_address = udp_server.recvfrom_into(buffer)
        data = buffer[:size]
        ip = client_address[0]
        print(f"Received message: {data.decode()} from {ip}")
        add_data_pack(ip, data.decode())
    except BlockingIOError:
        pass

# Update last hot times
def update_last_hot_times():
    global last_hot_time
    for ip, temp_str in clients_data.items():
        try:
            temp = float(temp_str)
        except:
            continue
        if temp >= TEMP_THRESHOLD:
            last_hot_time[ip] = time.time()

# Calculate ROS
def calculate_ros():
    global last_hot_time
    triggered_nodes = [(ip, last_hot_time[ip]) for ip in last_hot_time if last_hot_time[ip] > 0]
    
    if len(triggered_nodes) < 2:
        return 0.0, len(triggered_nodes)
    elif len(triggered_nodes) == 2:
        ip1, t1 = triggered_nodes[0]
        ip2, t2 = triggered_nodes[1]
        x1, y1 = get_node_location(ip1)
        x2, y2 = get_node_location(ip2)
        d = math.hypot(x2 - x1, y2 - y1)
        dt = abs(t2 - t1)
        if dt == 0:
            return 0.0, 2
        ros = d / dt
        return ros, 2
    else:
        X = []
        t_vec = []
        for ip, t in triggered_nodes:
            x, y = get_node_location(ip)
            X.append([x, y, 1])
            t_vec.append(t)
        a, b, c = np.linalg.lstsq(np.array(X), np.array(t_vec), rcond=None)[0]
        ros = 1 / math.sqrt(a**2 + b**2)
        return ros, len(triggered_nodes)

# Webpage generation
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
    <p>Rate of Spread: {:.2f} m/s | Hot nodes: {}</p>
    <table>
    <tr><th>Client IP</th><th>Latest Data</th></tr>
    """.format(rate_of_spread, hot_nodes_count)

    for ip, data in clients_data.items():
        html += f"<tr><td>{ip}</td><td>{data}</td></tr>"

    html += """
    </table>
    </body>
    </html>
    """
    return html

# Web server
def serve(buffer):
    try:
        readable, _, _ = select.select([web_socket], [], [], 0)
        if not readable:
            return
        connection, addr = web_socket.accept()
        readable, _, _ = select.select([connection], [], [], 2)
        if not readable:
            connection.close()
            return
        request = connection.recv_into(buffer)
        html = generate_page()
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{html}"
        connection.send(response.encode())
        connection.close()
    except OSError as e:
        if e.errno != 11:
            print(f"Webpage Error: {e}")

# Wi-Fi
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to Wi-Fi")

# UDP Server
pool = socketpool.SocketPool(wifi.radio)
udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
udp_server.setblocking(False)
print(f"UDP Server listening on {UDP_IP}:{UDP_PORT}")

# Adafruit IO
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)
print("Connected to Adafruit IO")

feeds = {
    "14": get_feed("picow14"),
    "141": get_feed("picow141"),
    "142": get_feed("picow142"),
    "42": get_feed("picow42")
}

# Initialize last_hot_time
for feed in feeds:
    ip = f"10.164.2.{feed}"
    last_hot_time[ip] = 0
    clients_data[ip] = "0"

# Webpage server
web_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
web_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
web_socket.bind((UDP_IP, 8080))
web_socket.listen(1)
web_socket.setblocking(False)
print(f"Web dashboard at http://{UDP_IP}:8080")

# Main loop
buffer = bytearray(1024)
last_send_time = 0

print("Waiting for data...")
try:
    while True:
        last_send_time = send_self_data(last_send_time)
        receive_data(buffer)
        update_last_hot_times()
        rate_of_spread, hot_nodes_count = calculate_ros()
        serve(buffer)
        time.sleep(0.05)
finally:
    udp_server.close()
    web_socket.close()
    print("Connection closed")
