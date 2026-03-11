import wifi
import socketpool

wifi.radio.connect("PraxisIII", "MiceAreNotRats")
print("Connected to Wi-Fi")
print("Server IP Address:", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

UDP_IP = str(wifi.radio.ipv4_address)
UDP_PORT = 5000
udp_server.bind((UDP_IP, UDP_PORT))
print(f"Server listening on {UDP_IP}:{UDP_PORT}")

buffer = bytearray(1024)  # ✅ pre-allocate buffer

try:
    while True:
        print("Waiting for data...")
        try:
            size, client_address = udp_server.recvfrom_into(buffer)  # ✅ use recvfrom_into
            data = buffer[:size]
            print(f"Received message: {data.decode()} from {client_address}")
            response = "Message received!"
            udp_server.sendto(response.encode(), client_address)
            print(f"Sent response to {client_address}")
        except Exception as e:
            print(f"Error: {e}")
finally:
    udp_server.close()
    print("Connection closed")
