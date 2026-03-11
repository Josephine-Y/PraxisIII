import wifi
import socketpool

# Connect to Wi-Fi
wifi.radio.connect("PraxisIII", "MiceAreNotRats")  # Replace with your Wi-Fi credentials
print("Connected to Wi-Fi")
print("Server IP Address:", wifi.radio.ipv4_address)

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Create a UDP socket
udp_server = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)

# Bind the server to an IP address and port
UDP_IP = str(wifi.radio.ipv4_address)  # Use the Pico W's IP address
UDP_PORT = 5000  # Port to listen on
udp_server.bind((UDP_IP, UDP_PORT))
print(f"Server listening on {UDP_IP}:{UDP_PORT}")

# Wait for incoming data
while True:
    print("Waiting for data...")
    try:
        data, client_address = udp_server.recvfrom(1024)  # Buffer size is 1024 bytes
        print(f"Received message: {data.decode()} from {client_address}")

        # Optionally, send a response back to the client
        response = "Message received!"
        udp_server.sendto(response.encode(), client_address)
        print(f"Sent response to {client_address}")
    except Exception as e:
        print(f"Error: {e}")
        exit()
         
finally:
    connection.close()
    server_socket.close()
    print("Connection closed")
    exit()

