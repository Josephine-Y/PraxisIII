import os
import wifi
import socketpool

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to Wi-Fi")
print("Server IP Address:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)

udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
udp_server.setblocking(False)

print(f"UDP Server listening on {UDP_IP}:{UDP_PORT}")

# HTTP server for online dashboard
http_server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
http_server.bind((UDP_IP, 80))
http_server.listen(1)
http_server.setblocking(False)

print(f"Web dashboard at http://{UDP_IP}")

buffer = bytearray(1024)

# store client data
clients_data = {}

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
    <tr><th>Client IP</th><th>Latest Data</th></tr>
    """

    for ip, data in clients_data.items():
        html += f"<tr><td>{ip}</td><td>{data}</td></tr>"

    html += """
    </table>
    </body>
    </html>
    """
    return html


try:
    while True:

        # ----- RECEIVE UDP DATA FROM CLIENT PICOS -----
        try:
            size, client_address = udp_server.recvfrom_into(buffer)
            data = buffer[:size].decode()

            client_ip = client_address[0]

            print(f"Received message: {data} from {client_ip}")

            # store latest message
            clients_data[client_ip] = data

            # send acknowledgement
            response = "Message received!"
            udp_server.sendto(response.encode(), client_address)

        except OSError:
            pass


        # ----- HANDLE WEB BROWSER REQUEST -----
        try:
            conn, addr = http_server.accept()
            print("Browser connected:", addr)

            request = conn.recv(1024)

            page = generate_page()

            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + page
            conn.send(response.encode())

            conn.close()

        except OSError:
            pass


finally:
    udp_server.close()
    http_server.close()
    print("Server closed")
